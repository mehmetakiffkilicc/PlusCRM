import abc
import os
import json
import time
import logging
from typing import Any, Generator
from decouple import config
from django.utils import timezone


# ---------------------------------------------------------------------------
# Ortak çıktı formatı — tüm provider'lar bu dict'leri yield eder
# ---------------------------------------------------------------------------
# {"type": "text",        "text": "..."}
# {"type": "tool_start",  "tool": "tool_name"}
# {"type": "tool_input",  "tool": "tool_name", "input_chunk": "..."}  (opsiyonel)
# {"type": "tool_call",   "tool": "tool_name", "params": {...}}
# {"type": "done"}
# {"type": "error",       "message": "..."}
# ---------------------------------------------------------------------------


class BaseLLMClient(abc.ABC):
    """
    Tüm LLM sağlayıcıları için ortak arayüz.
    Hangi model seçilirse seçilsin llm_view.py ve veritabanı altyapısı değişmez.
    """

    @abc.abstractmethod
    def stream_chat(
        self,
        messages: list,
        context: dict,
        system_prompt: str,
        tools: list = None,
    ) -> Generator[dict, None, None]:
        """
        Mesaj akışını normalize edilmiş dict'ler olarak yield eder.
        Her yield {'type': ..., ...} formatındadır.
        """

    @abc.abstractmethod
    def generate_summary(self, text: str, system_prompt: str) -> str:
        pass

    @abc.abstractmethod
    def generate_completion(self, prompt: str, system_prompt: str) -> str:
        pass

    def stream_completion(self, prompt: str, system_prompt: str) -> Generator[dict, None, None]:
        """Basit bir prompt için akış başlatır."""
        return self.stream_chat([{"role": "user", "content": prompt}], {}, system_prompt)

    def is_configured(self) -> bool:
        """API key'in tanımlı ve SDK'nın hazır olup olmadığını döndürür."""
        return True  # Alt sınıflar override eder


# ---------------------------------------------------------------------------
# Anthropic (Claude)
# ---------------------------------------------------------------------------

class AnthropicClient(BaseLLMClient):
    def __init__(self):
        import anthropic as _anthropic
        self.api_key = config('ANTHROPIC_API_KEY', default='')
        self.model = config('AI_DEFAULT_MODEL', default='claude-3-haiku-20240307')
        self.client = _anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    def stream_chat(
        self,
        messages: list,
        context: dict,
        system_prompt: str,
        tools: list = None,
        _tool_executor=None,
        _tool_executor_kwargs=None,
    ) -> Generator[dict, None, None]:
        if not self.client:
            yield {"type": "error", "message": "Anthropic API Key yapılandırılmamış."}
            return

        full_system = system_prompt
        if context:
            full_system += f"\n\nContext:\n{context}"

        kwargs = {
            "model": self.model,
            "max_tokens": 1024,
            "system": full_system,
            "messages": messages,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        stream = self.client.messages.create(**kwargs)
        current_tool = None

        for event in stream:
            etype = event.type

            if etype == "content_block_delta":
                delta = event.delta
                if delta.type == "text_delta":
                    yield {"type": "text", "text": delta.text}
                elif delta.type == "input_json_delta" and current_tool:
                    current_tool["raw_input"] += delta.partial_json

            elif etype == "content_block_start":
                block = event.content_block
                if block.type == "tool_use":
                    current_tool = {"name": block.name, "id": block.id, "raw_input": ""}
                    yield {"type": "tool_start", "tool": block.name}

            elif etype == "message_stop":
                if current_tool:
                    try:
                        params = json.loads(current_tool["raw_input"] or "{}")
                    except Exception:
                        params = {}
                    yield {"type": "tool_call", "tool": current_tool["name"], "params": params}
                    current_tool = None

        yield {"type": "done"}

    def generate_summary(self, text: str, system_prompt: str) -> str:
        if not self.client:
            return "Anthropic API Key yapılandırılmamış."
        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Şu veriyi özetle:\n{text}"}],
        )
        return response.content[0].text if response.content else ""

    def generate_completion(self, prompt: str, system_prompt: str) -> str:
        if not self.client:
            return "Anthropic API Key yapılandırılmamış."
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text if response.content else ""

    def is_configured(self) -> bool:
        return self.client is not None


# ---------------------------------------------------------------------------
# Gemini (Google)
# ---------------------------------------------------------------------------

class GeminiClient(BaseLLMClient):
    """
    Google Gemini adapter — yeni google-genai SDK (>=1.0) kullanır.
    .env: GEMINI_API_KEY, AI_DEFAULT_MODEL=gemini-2.0-flash
    """

    # Anthropic tool schema → Gemini Tool dönüşümü
    @staticmethod
    def _to_gemini_tools(tools_def: list):
        try:
            from google.genai import types as gtypes
        except ImportError:
            return None

        declarations = []
        for t in tools_def:
            schema = t.get("input_schema", {})
            props = {}
            for k, v in schema.get("properties", {}).items():
                raw_type = v.get("type", "string").lower()
                type_map = {
                    "string": "STRING", "integer": "INTEGER",
                    "number": "NUMBER", "boolean": "BOOLEAN",
                    "array": "ARRAY", "object": "OBJECT",
                }
                props[k] = gtypes.Schema(
                    type=type_map.get(raw_type, "STRING"),
                    description=v.get("description", ""),
                )
            declarations.append(
                gtypes.FunctionDeclaration(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters=gtypes.Schema(
                        type="OBJECT",
                        properties=props,
                        required=schema.get("required", []),
                    ),
                )
            )
        return [gtypes.Tool(function_declarations=declarations)]

    def __init__(self):
        self.api_key = config('GEMINI_API_KEY', default='')
        self.model_name = config('AI_DEFAULT_MODEL', default='gemini-2.0-flash')
        self._sdk = None
        if self.api_key:
            try:
                from google import genai as _genai
                self._sdk = _genai.Client(api_key=self.api_key)
            except ImportError:
                pass

    def _build_contents(self, messages: list, context: dict):
        """Anthropic mesaj formatını Gemini contents listesine çevirir."""
        from google.genai import types as gtypes
        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append(gtypes.Content(role=role, parts=[gtypes.Part(text=m["content"])]))
        # Context'i son user mesajına ekle
        if context and contents and contents[-1].role == "user":
            extra = f"\n\nContext:\n{json.dumps(context, ensure_ascii=False)}"
            last_text = contents[-1].parts[0].text + extra
            contents[-1] = gtypes.Content(role="user", parts=[gtypes.Part(text=last_text)])
        return contents

    FALLBACK_MODEL = "gemini-2.0-flash"

    def _call_with_retry(self, model, contents, config, max_retries=3):
        """generate_content çağrısını 503/429'da retry eder, sonra fallback modele geçer."""
        logger = logging.getLogger(__name__)
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self._sdk.models.generate_content(
                    model=model, contents=contents, config=config,
                )
                return response, model
            except Exception as e:
                code = getattr(e, 'code', None)
                if code in (429, 503):
                    last_error = e
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt  # 1s, 2s, 4s
                        logger.warning(
                            f"Gemini {model} → {code}, retry {attempt+1}/{max_retries} in {wait}s"
                        )
                        time.sleep(wait)
                    continue
                raise

        # Tüm retry'lar bitti — fallback modele geç
        if model != self.FALLBACK_MODEL:
            logger.warning(f"Gemini {model} retry tükendi, fallback → {self.FALLBACK_MODEL}")
            for fb_attempt in range(2):
                try:
                    response = self._sdk.models.generate_content(
                        model=self.FALLBACK_MODEL, contents=contents, config=config,
                    )
                    return response, self.FALLBACK_MODEL
                except Exception as fb_e:
                    fb_code = getattr(fb_e, 'code', None)
                    if fb_code in (429, 503) and fb_attempt == 0:
                        logger.warning(f"Fallback {self.FALLBACK_MODEL} → {fb_code}, retry 1 kez daha...")
                        time.sleep(2)
                        continue
                    last_error = fb_e
                    break

        raise last_error

    def stream_chat(
        self,
        messages: list,
        context: dict,
        system_prompt: str,
        tools: list = None,
        _tool_executor=None,
        _tool_executor_kwargs=None,
    ) -> Generator[dict, None, None]:
        if not self._sdk:
            yield {"type": "error", "message": "GEMINI_API_KEY yapılandırılmamış veya google-genai paketi yüklü değil."}
            return

        try:
            from google.genai import types as gtypes

            config_kwargs = {"system_instruction": system_prompt}
            if tools:
                gemini_tools = self._to_gemini_tools(tools)
                if gemini_tools:
                    config_kwargs["tools"] = gemini_tools

            contents = self._build_contents(messages, context)
            gen_config = gtypes.GenerateContentConfig(**config_kwargs)

            # Tool call döngüsü: en fazla 5 tur (sonsuz döngü koruması)
            total_input_tokens = 0
            total_output_tokens = 0
            for _round in range(5):
                response, _used_model = self._call_with_retry(
                    self.model_name, contents, gen_config,
                )

                # Token kullanımını topla
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    um = response.usage_metadata
                    total_input_tokens += getattr(um, 'prompt_token_count', 0) or 0
                    total_output_tokens += getattr(um, 'candidates_token_count', 0) or 0

                if not response.candidates or not response.candidates[0].content:
                    break

                parts = response.candidates[0].content.parts
                if not parts:
                    break

                # Model yanıtını konuşma geçmişine ekle
                contents.append(gtypes.Content(role="model", parts=parts))

                tool_calls_this_round = []

                for part in parts:
                    if part.text:
                        # Metni yield et
                        yield {"type": "text", "text": part.text}

                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        params = dict(fc.args) if fc.args else {}
                        yield {"type": "tool_start", "tool": fc.name}
                        yield {"type": "tool_call", "tool": fc.name, "params": params}
                        tool_calls_this_round.append((fc.name, params))

                if not tool_calls_this_round:
                    # Tool yok → cevap tamamlandı
                    break

                # Tool sonuçlarını çalıştır ve Gemini'ye geri besle
                if _tool_executor is None:
                    # Executor verilmediyse tool call'ları yield edip dur
                    # (llm_view eski davranışla handle eder)
                    break

                function_response_parts = []
                for tool_name, tool_params in tool_calls_this_round:
                    try:
                        kwargs = _tool_executor_kwargs or {}
                        result_raw = _tool_executor(tool_name, tool_params, **kwargs)
                        try:
                            result_dict = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
                        except Exception:
                            result_dict = {"result": str(result_raw)}
                        yield {"type": "tool_result", "tool": tool_name, "result": result_dict}
                        function_response_parts.append(
                            gtypes.Part.from_function_response(
                                name=tool_name,
                                response=result_dict if isinstance(result_dict, dict) else {"result": result_dict},
                            )
                        )
                    except Exception as te:
                        yield {"type": "tool_result", "tool": tool_name, "result": {"error": str(te)}}
                        function_response_parts.append(
                            gtypes.Part.from_function_response(
                                name=tool_name,
                                response={"error": str(te)},
                            )
                        )

                # Tool sonuçlarını user turn olarak ekle
                if function_response_parts:
                    contents.append(gtypes.Content(role="user", parts=function_response_parts))
                # Bir sonraki round: Gemini tool sonucunu okuyup metin üretecek

            yield {"type": "done", "input_tokens": total_input_tokens, "output_tokens": total_output_tokens}

        except Exception as e:
            logging.getLogger(__name__).error(f"Gemini stream_chat error: {e}", exc_info=True)
            code = getattr(e, 'code', None)
            if code in (429, 503):
                yield {"type": "error", "message": "AI servisi şu an yoğun. Lütfen birkaç dakika sonra tekrar deneyin."}
            else:
                yield {"type": "error", "message": str(e)}

    def generate_summary(self, text: str, system_prompt: str) -> str:
        if not self._sdk:
            return "GEMINI_API_KEY yapılandırılmamış."
        try:
            from google.genai import types as gtypes
            response, _ = self._call_with_retry(
                self.model_name,
                f"Şu veriyi özetle:\n{text}",
                gtypes.GenerateContentConfig(system_instruction=system_prompt),
            )
            return response.text or ""
        except Exception as e:
            # MultiLLM fallback'ini tetiklemek için exception fırlatıyoruz
            raise Exception(f"Gemini API Error: {e}")

    def generate_completion(self, prompt: str, system_prompt: str) -> str:
        if not self._sdk:
            return "GEMINI_API_KEY yapılandırılmamış."
        try:
            from google.genai import types as gtypes
            response, _ = self._call_with_retry(
                self.model_name,
                prompt,
                gtypes.GenerateContentConfig(system_instruction=system_prompt),
            )
            return response.text or ""
        except Exception as e:
            # MultiLLM fallback'ini tetiklemek için exception fırlatıyoruz
            raise Exception(f"Gemini API Error: {e}")

    def is_configured(self) -> bool:
        return self._sdk is not None


# ---------------------------------------------------------------------------
# OpenAI (hazır iskelet — ileride doldurulur)
# ---------------------------------------------------------------------------

class OpenAIClient(BaseLLMClient):
    def stream_chat(self, messages, context, system_prompt, tools=None):
        yield {"type": "error", "message": "OpenAI entegrasyonu henüz tamamlanmadı."}

    def generate_summary(self, text, system_prompt):
        raise NotImplementedError()

    def generate_completion(self, prompt, system_prompt):
        raise NotImplementedError()


class OpenRouterClient(BaseLLMClient):
    """
    OpenRouter adapter — OpenAI uyumlu API üzerinden birçok modele erişim sağlar.
    Yedekleme (failover) için idealdir.
    """
    def __init__(self, model_override: str = None):
        self.api_key = config('OPENROUTER_API_KEY', default='')
        self.model = model_override or config('OPENROUTER_MODEL', default='openai/chatgpt-4o-latest')
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def stream_chat(self, messages, context, system_prompt, tools=None, _tool_executor=None, _tool_executor_kwargs=None) -> Generator[dict, None, None]:
        if not self.api_key:
            yield {"type": "error", "message": "OPENROUTER_API_KEY yapılandırılmamış."}
            return

        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://crm-ai-asistan.com",
            "X-Title": "CRM AI Asistan",
        }
        
        formatted_messages = [{"role": "system", "content": system_prompt}]
        if context:
            formatted_messages[0]["content"] += f"\n\nContext:\n{json.dumps(context, ensure_ascii=False)}"
        
        for m in messages:
            formatted_messages.append({"role": m["role"], "content": m["content"]})

        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": True,
            "temperature": 0.1,
            "top_p": 0.9,
        }

        if tools:
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", t.get("parameters", {"type": "object", "properties": {}}))
                    }
                })
            payload["tools"] = openai_tools

        try:
            # Tool-use Döngüsü (En fazla 5 tur)
            for _round in range(5):
                response = requests.post(self.base_url, headers=headers, json=payload, stream=True, timeout=60)
                response.raise_for_status()

                active_tool_calls = {}
                full_text_this_round = ""
                has_content = False

                for line in response.iter_lines():
                    if not line: continue
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str.strip() == '[DONE]': break
                        try:
                            chunk = json.loads(data_str)
                            if not chunk.get('choices'): continue
                            delta = chunk['choices'][0].get('delta', {})
                            
                            content = delta.get('content')
                            if content:
                                full_text_this_round += content
                                yield {"type": "text", "text": content}
                                has_content = True
                            
                            tool_calls = delta.get('tool_calls')
                            if tool_calls:
                                has_content = True
                                for tc in tool_calls:
                                    idx = tc.get('index', 0)
                                    if idx not in active_tool_calls:
                                        active_tool_calls[idx] = {"id": tc.get("id", ""), "name": "", "args": ""}
                                    func = tc.get('function', {})
                                    if func.get('name'):
                                        active_tool_calls[idx]["name"] = func['name']
                                        yield {"type": "tool_start", "tool": func['name']}
                                    if func.get('arguments'):
                                        active_tool_calls[idx]["args"] += func['arguments']
                        except: continue

                # Self-Healing: Eğer model native tool-call yerine metin içinde TOOLCALL> kullandıysa ayıkla
                if not active_tool_calls and "TOOLCALL>" in full_text_this_round:
                    import re
                    # Örnek: TOOLCALL>[{"name": "...", "arguments": {...}}]
                    match = re.search(r'TOOLCALL>\s*(\[.*?\]|\{.*?\})', full_text_this_round, re.DOTALL)
                    if match:
                        try:
                            manual_calls = json.loads(match.group(1))
                            if isinstance(manual_calls, dict): manual_calls = [manual_calls]
                            for idx, mc in enumerate(manual_calls):
                                active_tool_calls[idx] = {
                                    "id": f"manual_{idx}_{int(timezone.now().timestamp())}",
                                    "name": mc.get("name", ""),
                                    "args": json.dumps(mc.get("arguments", mc.get("params", {})))
                                }
                        except: pass

                # Model yanıtını mesaj geçmişine ekle
                assistant_msg = {"role": "assistant", "content": full_text_this_round or ""}
                if active_tool_calls:
                    assistant_msg["tool_calls"] = []
                    for idx, tc in active_tool_calls.items():
                        # Bazı modeller ID üretmeyebilir, bu durumda rastgele bir ID atıyoruz (OpenAI formatı şart koşar)
                        call_id = tc.get("id") or f"call_{idx}_{int(timezone.now().timestamp())}"
                        assistant_msg["tool_calls"].append({
                            "id": call_id, "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["args"]}
                        })
                        active_tool_calls[idx]["id"] = call_id # ID'yi güncelle ki bir sonraki adımda kullanılabilsin
                payload["messages"].append(assistant_msg)

                if not active_tool_calls:
                    break # Tool yoksa bitti

                # Araçları çalıştır ve sonuçları ekle
                if not _tool_executor: break

                for idx, tc in active_tool_calls.items():
                    name = tc["name"]
                    try:
                        args = json.loads(tc["args"])
                    except:
                        args = {}
                    
                    yield {"type": "tool_call", "tool": name, "params": args}
                    
                    try:
                        res = _tool_executor(name, args, **(_tool_executor_kwargs or {}))
                        try:
                            res_dict = json.loads(res) if isinstance(res, str) else res
                        except:
                            res_dict = {"result": str(res)}
                        
                        yield {"type": "tool_result", "tool": name, "result": res_dict}
                        payload["messages"].append({
                            "role": "tool", "tool_call_id": tc["id"],
                            "name": name, "content": json.dumps(res_dict, ensure_ascii=False)
                        })
                    except Exception as te:
                        yield {"type": "tool_result", "tool": name, "result": {"error": str(te)}}
                        payload["messages"].append({
                            "role": "tool", "tool_call_id": tc["id"],
                            "name": name, "content": json.dumps({"error": str(te)})
                        })

                if not has_content and not active_tool_calls:
                    break # Hiçbir şey gelmediyse sonsuz döngüden kaç
                
            yield {"type": "done"}
        except Exception as e:
            yield {"type": "error", "message": f"OpenRouter Hatası: {str(e)}"}

    def _call_sync(self, messages, system_prompt):
        import requests
        import time
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "stream": False
        }
        
        last_error = None
        for attempt in range(2):
            try:
                response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
            except Exception as e:
                last_error = e
                # 503 veya 429 ise bekle ve tekrar dene (OpenRouter için)
                status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                if status_code in (429, 503, 502) and attempt == 0:
                    import time
                    time.sleep(4)
                    continue
                raise last_error

    def generate_summary(self, text, system_prompt):
        return self._call_sync([{"role": "user", "content": f"Özetle: {text}"}], system_prompt)

    def generate_completion(self, prompt, system_prompt):
        return self._call_sync([{"role": "user", "content": prompt}], system_prompt)

    def stream_completion(self, prompt, system_prompt):
        return self.stream_chat([{"role": "user", "content": prompt}], {}, system_prompt)


class MultiLLMClient(BaseLLMClient):
    """
    Hata payı düşük, çok kademeli yedekli LLM istemcisi.
    Listedeki sağlayıcıları sırasıyla dener, bir hata olması durumunda bir sonrakine geçer.
    """
    def __init__(self, clients: list[BaseLLMClient]):
        self.clients = [c for c in clients if c.is_configured()]

    def stream_chat(self, messages, context, system_prompt, tools=None, _tool_executor=None, _tool_executor_kwargs=None):
        last_error = "Yapılandırılmış AI istemcisi bulunamadı."
        
        for i, client in enumerate(self.clients):
            try:
                # Hata durumunu takip etmek için bir bayrak
                has_error = False
                yielded_any = False

                for chunk in client.stream_chat(
                    messages, context, system_prompt, tools,
                    _tool_executor=_tool_executor,
                    _tool_executor_kwargs=_tool_executor_kwargs,
                ):
                    if chunk.get("type") == "error":
                        last_error = chunk.get("message", f"Client {i} error")
                        has_error = True
                        break
                    
                    # İlk gerçek veri geldiğinde, eğer fallback ise not düş
                    if not yielded_any and i > 0 and chunk.get("type") in ("text", "tool_start", "tool_call"):
                        model_name = getattr(client, 'model', 'Yedek')
                        yield {"type": "text", "text": f"💡 *Not: Birincil AI servisi yoğun olduğu için {i}. yedek üzerinden yanıt alıyorsunuz ({model_name}).*\n\n"}
                    
                    if chunk.get("type") in ("text", "tool_start", "tool_call", "tool_result"):
                        yielded_any = True
                    
                    yield chunk

                if not has_error:
                    # Başarıyla tamamlandı
                    return
                
                # Hata varsa ve daha önce veri yield edildiyse, akış bozulduğu için durmak zorundayız
                # Ancak i. denemede hata alıp hiç veri yield edilmediyse bir sonrakine geçebiliriz
                if yielded_any:
                    return 

            except Exception as e:
                last_error = str(e)
                logging.getLogger(__name__).warning(f"Client {i} failed: {last_error}")
                continue

        yield {"type": "error", "message": f"Tüm AI servisleri erişilemez durumda: {last_error}"}

    def generate_summary(self, text, system_prompt):
        last_error = None
        for client in self.clients:
            try:
                return client.generate_summary(text, system_prompt)
            except Exception as e:
                last_error = e
                continue
        raise Exception(f"Tüm AI servisleri başarısız: {last_error}")

    def generate_completion(self, prompt, system_prompt):
        last_error = None
        import time
        for i, client in enumerate(self.clients):
            try:
                return client.generate_completion(prompt, system_prompt)
            except Exception as e:
                last_error = e
                logging.getLogger(__name__).warning(f"Completion Client {i} failed: {e}")
                if i < len(self.clients) - 1:
                    time.sleep(1) # Failover öncesi bekle
                continue
        raise Exception(f"Tüm AI servisleri başarısız: {last_error}")

    def stream_completion(self, prompt, system_prompt):
        """Streaming failover desteği ile completion."""
        last_error = "Yapılandırılmış AI istemcisi bulunamadı."
        for i, client in enumerate(self.clients):
            try:
                yielded_any = False
                for chunk in client.stream_completion(prompt, system_prompt):
                    if chunk.get("type") == "error":
                        last_error = chunk.get("message", f"Client {i} error")
                        break
                    
                    if not yielded_any and i > 0 and chunk.get("type") == "text":
                         yield {"type": "text", "text": f"💡 *Failover ({i}. yedek) aktif.*\n\n"}

                    if chunk.get("type") == "text":
                        yielded_any = True
                    yield chunk
                
                if yielded_any: return
            except Exception as e:
                last_error = str(e)
                continue
        yield {"type": "error", "message": f"Tüm AI servisleri başarısız: {last_error}"}

    def is_configured(self):
        return any(c.is_configured() for c in self.clients)


# ---------------------------------------------------------------------------
# Factory — .env'deki LLM_PROVIDER'a göre doğru client'ı döner
# ---------------------------------------------------------------------------

def get_llm_client() -> BaseLLMClient:
    """
    Aktif LLM_PROVIDER'a göre doğru client'ı döndürür.
    Varsayılan: MultiLLMClient (Gemini -> OpenRouter failover aktif)
    """
    provider = config('LLM_PROVIDER', default='gemini').lower()

    if provider == 'anthropic':
        return AnthropicClient()
    
    if provider == 'openrouter':
        return OpenRouterClient()
    
    # Triple Failover Optimization: Kalite ve Dil Tutarlılığı Odaklı
    clients = [GeminiClient()]
    
    # .env'den gelen özel model varsa onu önceliğe al
    env_model = config('OPENROUTER_MODEL', default=None)
    if env_model:
        clients.append(OpenRouterClient(model_override=env_model))
    
    # Güçlü ve Güvenilir Ücretsiz Yedekler
    clients.extend([
        OpenRouterClient(model_override="google/gemini-2.0-flash-lite-001:free"), # En stabil ücretsiz model
        OpenRouterClient(model_override="meta-llama/llama-3.1-70b-instruct:free"), # Büyük ve çok dilli başarısı yüksek
        OpenRouterClient(model_override="meta-llama/llama-3.3-70b-instruct:free"), 
        OpenRouterClient(model_override="mistralai/pixtral-12b:free"),
        OpenRouterClient(model_override="google/gemma-2-9b-it:free"),              # Alternatif Gemma
        OpenRouterClient(model_override="openrouter/free"),                      # SADECE son çare
    ])
    
    return MultiLLMClient(clients=clients)
