import { useState } from 'react'
import { Button, ActionIcon, Tooltip } from '@mantine/core'
import { IconFileSpreadsheet } from '@tabler/icons-react'
import apiClient from '../api/client'

interface ExcelExportButtonProps {
    url: string
    filename?: string
    label?: string
    variant?: 'button' | 'icon'
    color?: string
    disabled?: boolean
    size?: string
}

export default function ExcelExportButton({
    url,
    filename = 'Liste.xlsx',
    label = 'Excel İndir',
    variant = 'button',
    color = 'green',
    disabled = false,
    size = 'xs',
}: ExcelExportButtonProps) {
    const [exporting, setExporting] = useState(false)

    const handleExport = async () => {
        setExporting(true)
        try {
            const response = await apiClient.get(url, { responseType: 'blob' })
            const blob = response.data instanceof Blob
                ? response.data
                : new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })

            const disposition = response.headers['content-disposition']
            let downloadName = filename
            if (disposition) {
                const utf8Match = disposition.match(/filename\*=UTF-8''(.+)/i)
                const plainMatch = disposition.match(/filename="?([^"]+)"?/)
                if (utf8Match) downloadName = decodeURIComponent(utf8Match[1])
                else if (plainMatch) downloadName = plainMatch[1]
            }

            const objectUrl = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = objectUrl
            a.download = downloadName
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(objectUrl)
            document.body.removeChild(a)
        } catch {
            alert('Excel dosyası oluşturulurken bir hata oluştu.')
        } finally {
            setExporting(false)
        }
    }

    if (variant === 'icon') {
        return (
            <Tooltip label={exporting ? 'Hazırlanıyor...' : label}>
                <ActionIcon
                    variant="light"
                    color={color}
                    size={size}
                    loading={exporting}
                    disabled={disabled}
                    onClick={handleExport}
                >
                    <IconFileSpreadsheet size={16} />
                </ActionIcon>
            </Tooltip>
        )
    }

    return (
        <Button
            variant="light"
            color={color}
            size={size}
            leftSection={<IconFileSpreadsheet size={16} />}
            loading={exporting}
            disabled={disabled}
            onClick={handleExport}
        >
            {exporting ? 'Hazırlanıyor...' : label}
        </Button>
    )
}
