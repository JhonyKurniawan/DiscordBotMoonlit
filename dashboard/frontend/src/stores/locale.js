import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// Translation files
const translations = {
    en: {
        // Sidebar
        sidebar: {
            general: 'General',
            leveling: 'Leveling',
            chatbot: 'Chatbot',
            music: 'Music',
            moderation: 'Moderation',
            logs: 'Logs',
            settings: 'Settings'
        },
        // Settings page
        settings: {
            title: 'Bot Settings',
            subtitle: 'Configure bot preferences and behavior',
            preferences: 'Preferences',
            language: 'Dashboard Language',
            languagePlaceholder: 'Select language',
            prefix: 'Command Prefix',
            deleteMessages: 'Delete Command Messages',
            deleteMessagesDesc: 'Automatically delete command invocations',
            notifications: 'Notifications',
            dmLevelUp: 'DM on Level Up',
            dmLevelUpDesc: 'Send DM to users when they level up',
            dmModeration: 'DM on Moderation Action',
            dmModerationDesc: 'Notify users when they receive moderation actions',
            dangerZone: 'Danger Zone',
            resetSettings: 'Reset Bot Settings',
            resetSettingsDesc: 'This will reset all bot settings to their default values. This action cannot be undone.',
            resetButton: 'Reset All Settings',
            clearData: 'Clear All Data',
            clearDataDesc: 'Delete all stored data including levels, warnings, and logs. This action cannot be undone.',
            clearButton: 'Clear Server Data'
        },
        // Common
        common: {
            save: 'Save Changes',
            cancel: 'Cancel',
            delete: 'Delete',
            add: 'Add',
            edit: 'Edit',
            enable: 'Enable',
            disable: 'Disable',
            unsavedChanges: 'You have unsaved changes'
        }
    },
    id: {
        // Sidebar
        sidebar: {
            general: 'Umum',
            leveling: 'Leveling',
            chatbot: 'Chatbot',
            music: 'Musik',
            moderation: 'Moderasi',
            logs: 'Log',
            settings: 'Pengaturan'
        },
        // Settings page
        settings: {
            title: 'Pengaturan Bot',
            subtitle: 'Konfigurasi preferensi dan perilaku bot',
            preferences: 'Preferensi',
            language: 'Bahasa Dashboard',
            languagePlaceholder: 'Pilih bahasa',
            prefix: 'Prefix Perintah',
            deleteMessages: 'Hapus Pesan Perintah',
            deleteMessagesDesc: 'Otomatis hapus pesan perintah',
            notifications: 'Notifikasi',
            dmLevelUp: 'DM saat Naik Level',
            dmLevelUpDesc: 'Kirim DM ke pengguna saat mereka naik level',
            dmModeration: 'DM saat Aksi Moderasi',
            dmModerationDesc: 'Beritahu pengguna saat menerima aksi moderasi',
            dangerZone: 'Zona Berbahaya',
            resetSettings: 'Reset Pengaturan Bot',
            resetSettingsDesc: 'Ini akan mereset semua pengaturan bot ke nilai default. Tindakan ini tidak dapat dibatalkan.',
            resetButton: 'Reset Semua Pengaturan',
            clearData: 'Hapus Semua Data',
            clearDataDesc: 'Hapus semua data termasuk level, peringatan, dan log. Tindakan ini tidak dapat dibatalkan.',
            clearButton: 'Hapus Data Server'
        },
        // Common
        common: {
            save: 'Simpan Perubahan',
            cancel: 'Batal',
            delete: 'Hapus',
            add: 'Tambah',
            edit: 'Edit',
            enable: 'Aktifkan',
            disable: 'Nonaktifkan',
            unsavedChanges: 'Ada perubahan yang belum disimpan'
        }
    },
    ja: {
        // Sidebar
        sidebar: {
            general: '一般',
            leveling: 'レベリング',
            chatbot: 'チャットボット',
            music: '音楽',
            moderation: 'モデレーション',
            logs: 'ログ',
            settings: '設定'
        },
        // Settings page
        settings: {
            title: 'ボット設定',
            subtitle: 'ボットの設定と動作を構成',
            preferences: '設定',
            language: 'ダッシュボード言語',
            languagePlaceholder: '言語を選択',
            prefix: 'コマンドプレフィックス',
            deleteMessages: 'コマンドメッセージを削除',
            deleteMessagesDesc: 'コマンド呼び出しを自動的に削除',
            notifications: '通知',
            dmLevelUp: 'レベルアップ時にDM',
            dmLevelUpDesc: 'レベルアップ時にユーザーにDMを送信',
            dmModeration: 'モデレーション時にDM',
            dmModerationDesc: 'モデレーションアクションを受けた時にユーザーに通知',
            dangerZone: '危険ゾーン',
            resetSettings: 'ボット設定をリセット',
            resetSettingsDesc: 'すべてのボット設定をデフォルト値にリセットします。この操作は元に戻せません。',
            resetButton: 'すべての設定をリセット',
            clearData: 'すべてのデータを消去',
            clearDataDesc: 'レベル、警告、ログを含むすべてのデータを削除します。この操作は元に戻せません。',
            clearButton: 'サーバーデータを消去'
        },
        // Common
        common: {
            save: '変更を保存',
            cancel: 'キャンセル',
            delete: '削除',
            add: '追加',
            edit: '編集',
            enable: '有効',
            disable: '無効',
            unsavedChanges: '未保存の変更があります'
        }
    },
    ko: {
        // Sidebar
        sidebar: {
            general: '일반',
            leveling: '레벨링',
            chatbot: '챗봇',
            music: '음악',
            moderation: '관리',
            logs: '로그',
            settings: '설정'
        },
        // Settings page
        settings: {
            title: '봇 설정',
            subtitle: '봇 환경설정 및 동작 구성',
            preferences: '환경설정',
            language: '대시보드 언어',
            languagePlaceholder: '언어 선택',
            prefix: '명령어 접두사',
            deleteMessages: '명령어 메시지 삭제',
            deleteMessagesDesc: '명령어 호출을 자동으로 삭제',
            notifications: '알림',
            dmLevelUp: '레벨업 시 DM',
            dmLevelUpDesc: '레벨업 시 사용자에게 DM 전송',
            dmModeration: '관리 조치 시 DM',
            dmModerationDesc: '관리 조치를 받을 때 사용자에게 알림',
            dangerZone: '위험 구역',
            resetSettings: '봇 설정 초기화',
            resetSettingsDesc: '모든 봇 설정을 기본값으로 초기화합니다. 이 작업은 되돌릴 수 없습니다.',
            resetButton: '모든 설정 초기화',
            clearData: '모든 데이터 삭제',
            clearDataDesc: '레벨, 경고, 로그를 포함한 모든 데이터를 삭제합니다. 이 작업은 되돌릴 수 없습니다.',
            clearButton: '서버 데이터 삭제'
        },
        // Common
        common: {
            save: '변경사항 저장',
            cancel: '취소',
            delete: '삭제',
            add: '추가',
            edit: '편집',
            enable: '활성화',
            disable: '비활성화',
            unsavedChanges: '저장되지 않은 변경사항이 있습니다'
        }
    }
}

export const useLocaleStore = defineStore('locale', () => {
    // Current locale (default to 'en')
    const currentLocale = ref(localStorage.getItem('dashboard_locale') || 'en')

    // Get translation by key path (e.g., 'settings.title')
    function t(key) {
        const keys = key.split('.')
        let result = translations[currentLocale.value]

        for (const k of keys) {
            if (result && result[k]) {
                result = result[k]
            } else {
                // Fallback to English
                result = translations['en']
                for (const k2 of keys) {
                    if (result && result[k2]) {
                        result = result[k2]
                    } else {
                        return key // Return key if not found
                    }
                }
                break
            }
        }

        return result
    }

    // Set locale
    function setLocale(locale) {
        if (translations[locale]) {
            currentLocale.value = locale
            localStorage.setItem('dashboard_locale', locale)
        }
    }

    // Available locales
    const availableLocales = computed(() => [
        { value: 'en', label: 'English' },
        { value: 'id', label: 'Bahasa Indonesia' },
        { value: 'ja', label: '日本語' },
        { value: 'ko', label: '한국어' }
    ])

    return {
        currentLocale,
        t,
        setLocale,
        availableLocales
    }
})
