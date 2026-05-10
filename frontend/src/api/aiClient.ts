// API base URL'i ana client ile aynı mantıkla oluştur
const BASE_URL = (() => {
  let url = import.meta.env.VITE_API_URL || '/api';
  if (!url.endsWith('/api')) {
    url = url.endsWith('/') ? url + 'api' : url + '/api';
  }
  return url;
})();

class AIClient {
  private getToken() {
    return localStorage.getItem('auth_token');
  }

  public async getSessionHistory(sessionId: string) {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${BASE_URL}/ai/sohbet/gecmis/?session_id=${sessionId}`, { headers });
    if (!res.ok) throw new Error('Failed to load history');
    return res.json();
  }

  public async createNewSession() {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${BASE_URL}/ai/sohbet/yeni/`, { method: 'POST', headers });
    if (!res.ok) throw new Error('Failed to create session');
    return res.json();
  }

  public streamQuickSummary(
    payload: { text?: string, data?: any, context_type?: string, context_id?: string, data_source_id?: string | number },
    onToken: (token: string) => void,
    onError: (err: any) => void,
    onFinish: () => void
  ) {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const controller = new AbortController();

    fetch(`${BASE_URL}/ai/ozet/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...payload, stream: true }),
      signal: controller.signal
    }).then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
      }
      
      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader");
      
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (!dataStr || dataStr.trim() === '[DONE]') continue;
            try {
              const data = JSON.parse(dataStr);
              if (data.text) {
                onToken(data.text);
              } else if (data.error) {
                onError(new Error(data.error));
                return;
              }
            } catch (e) {
              console.error("SSE parse error", e, dataStr);
            }
          }
        }
      }
      onFinish();
    }).catch(err => {
      if (err.name !== 'AbortError') onError(err);
    });

    return () => controller.abort(); // Cancel function
  }

   public streamChat(
     sessionId: string,
     message: string,
     context: any,
     onToken: (token: string) => void,
     onError: (err: any) => void,
     onFinish: () => void,
     onTool?: (type: 'start' | 'running' | 'result', data: any) => void
   ) {
     const token = this.getToken();
     const headers: Record<string, string> = {
       'Content-Type': 'application/json',
     };
     if (token) headers['Authorization'] = `Bearer ${token}`;

     const controller = new AbortController();
     let timeoutId: NodeJS.Timeout | null = null;

     const cleanup = () => {
       if (timeoutId) clearTimeout(timeoutId);
     };

     // 180 saniye timeout - backend yanıt vermezse hata ver
     timeoutId = setTimeout(() => {
       controller.abort();
       onError(new Error('İstek zaman aşımına uğradı. Lütfen tekrar deneyin.'));
     }, 180000);

     fetch(`${BASE_URL}/ai/sohbet/`, {
       method: 'POST',
       headers,
       body: JSON.stringify({ session_id: sessionId, message, context }),
       signal: controller.signal
     }).then(async (response) => {
       if (!response.ok) {
         cleanup();
         throw new Error(`HTTP Error: ${response.status}`);
       }
       
       const reader = response.body?.getReader();
       if (!reader) {
         cleanup();
         throw new Error("No reader");
       }
       
       const decoder = new TextDecoder("utf-8");
       let buffer = "";

       while (true) {
         const { done, value } = await reader.read();
         if (done) {
           cleanup();
           break;
         }
         
         buffer += decoder.decode(value, { stream: true });
         const lines = buffer.split("\n");
         buffer = lines.pop() || "";
         
         for (const line of lines) {
           if (line.startsWith("data: ")) {
             const dataStr = line.slice(6);
             if (!dataStr) continue;
             try {
               const data = JSON.parse(dataStr);
               if (data.type === 'message') {
                 onToken(data.text);
               } else if (data.type === 'tool_start') {
                 onTool?.('start', data.tool);
               } else if (data.type === 'tool_running') {
                 onTool?.('running', data.tool);
               } else if (data.type === 'tool_result') {
                 onTool?.('result', data);
               } else if (data.type === 'error') {
                 cleanup();
                 onError(new Error(data.message));
                 return;
               } else if (data.type === 'done') {
                 cleanup();
                 onFinish();
                 return;
               }
             } catch (e) {
               console.error("SSE parse error", e, dataStr);
             }
           }
         }
       }
       cleanup();
       onFinish();
     }).catch(err => {
       cleanup();
       if (err.name !== 'AbortError') onError(err);
     });

     return () => {
       cleanup();
       controller.abort();
     }; // Cancel function
   }

  public async getScheduledCampaigns() {
    const token = this.getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/ai/kampanya/listele/`, { headers });
    return res.json();
  }

  public async scheduleCampaign(data: any) {
    const token = this.getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/ai/kampanya/planla/`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
    return res.json();
  }

  public async deleteScheduledCampaign(id: number) {
    const token = this.getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/ai/kampanya/${id}/sil/`, { method: 'DELETE', headers });
    return res.json();
  }

  public async runScheduledCampaign(id: number) {
    const token = this.getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/ai/kampanya/${id}/calistir/`, { method: 'POST', headers });
    return res.json();
  }

  public async getCustomerNBA(customerId: string | number, dataSourceId: string | number = 0) {
    const token = this.getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/ai/customer-nba/${customerId}/?data_source_id=${dataSourceId}`, { headers });
    if (!res.ok) throw new Error('NBA fetch failed');
    return res.json();
  }

  public async generateCampaignVariants(campaignDetail: any) {
    const token = this.getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/ai/varyant-uret/`, {
      method: 'POST',
      headers,
      body: JSON.stringify(campaignDetail)
    });
    
    if (!res.ok) {
      let errorMsg = 'Variant generation failed';
      try {
        const errJson = await res.json();
        errorMsg = errJson.error || errJson.detail || errorMsg;
      } catch (e) {
        // Fallback to text if JSON parse fails
        try {
          const errText = await res.text();
          if (errText) errorMsg = errText;
        } catch (e2) {}
      }
      throw new Error(errorMsg);
    }
    
    return res.json();
  }

  public async getWeeklyBrief(dataSourceId: number | string) {
    const token = this.getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${BASE_URL}/ai/haftalik-brifing/?veri_kaynagi_id=${dataSourceId}`, { headers });
    if (!res.ok) throw new Error('Brief fetch failed');
    return res.json();
  }
}

export const aiClient = new AIClient();
