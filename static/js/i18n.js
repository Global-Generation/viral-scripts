// === i18n: EN/RU translation system ===
const I18N = {
    // Sidebar
    'nav.scripts':          { en: 'Scripts',            ru: 'Сценарии' },
    'nav.search':           { en: 'Search',             ru: 'Поиск' },
    'nav.scripts_library':  { en: 'Scripts Library',    ru: 'Библиотека скриптов' },
    'nav.avatars_section':  { en: 'Avatars',            ru: 'Аватары' },
    'nav.avatar_gallery':   { en: 'Avatar Gallery',     ru: 'Галерея аватаров' },
    'nav.videos_section':   { en: 'Videos',             ru: 'Видео' },
    'nav.all_videos':       { en: 'All Videos',         ru: 'Все видео' },
    'nav.settings':         { en: 'Settings',           ru: 'Настройки' },
    'nav.presets':          { en: 'Presets',             ru: 'Пресеты' },
    'nav.api_keys':         { en: 'API Keys & Usage',   ru: 'API ключи и использование' },
    'sidebar.title':        { en: 'Viral Scripts',      ru: 'Viral Scripts' },
    'sidebar.sub':          { en: 'TikTok Script Analyzer', ru: 'Анализатор TikTok скриптов' },

    // Dashboard
    'dash.title':           { en: 'Find Viral TikTok Scripts',  ru: 'Поиск вирусных TikTok скриптов' },
    'dash.subtitle':        { en: 'Search trending TikTok videos, extract scripts, make them more provocative', ru: 'Поиск трендовых TikTok видео, извлечение скриптов, создание провокативных версий' },
    'dash.search_ph':       { en: 'Search TikTok videos...',    ru: 'Поиск TikTok видео...' },
    'dash.search_btn':      { en: 'Search',             ru: 'Поиск' },
    'dash.ai_label':        { en: 'Artificial Intelligence',  ru: 'Искусственный интеллект' },
    'dash.finance_label':   { en: 'Money & Investing',  ru: 'Деньги и инвестиции' },
    'dash.recent':          { en: 'Recent Searches',    ru: 'Недавние поиски' },
    'dash.no_presets':      { en: 'No presets yet.',    ru: 'Пресетов пока нет.' },
    'dash.add_some':        { en: 'Add some',           ru: 'Добавить' },

    // Table headers
    'th.query':             { en: 'Query',              ru: 'Запрос' },
    'th.category':          { en: 'Category',           ru: 'Категория' },
    'th.results':           { en: 'Results',            ru: 'Результаты' },
    'th.date':              { en: 'Date',               ru: 'Дата' },
    'th.script_preview':    { en: 'Script Preview',     ru: 'Превью скрипта' },
    'th.video':             { en: 'Video',              ru: 'Видео' },
    'th.score':             { en: 'Score',              ru: 'Оценка' },
    'th.prompt':            { en: 'Prompt',             ru: 'Промпт' },
    'th.status':            { en: 'Status',             ru: 'Статус' },
    'th.video_title':       { en: 'Video Title',        ru: 'Название видео' },

    // Buttons
    'btn.view':             { en: 'View',               ru: 'Открыть' },
    'btn.del':              { en: 'Del',                ru: 'Удал.' },
    'btn.add':              { en: 'Add',                ru: 'Добавить' },
    'btn.copy':             { en: 'Copy',               ru: 'Копировать' },
    'btn.save':             { en: 'Save Changes',       ru: 'Сохранить' },
    'btn.publish':          { en: 'Publish',            ru: 'Опубликовать' },
    'btn.unpublish':        { en: 'Unpublish',          ru: 'Снять публикацию' },
    'btn.clear':            { en: 'Clear',              ru: 'Сбросить' },
    'btn.unassign':         { en: 'Unassign',           ru: 'Снять' },
    'btn.classify':         { en: 'Classify',           ru: 'Классифицировать' },
    'btn.reclassify':       { en: 'Re-classify',        ru: 'Переклассифицировать' },
    'btn.score':            { en: 'Score',              ru: 'Оценить' },
    'btn.rescore':          { en: 'Re-score',           ru: 'Переоценить' },
    'btn.make_provocative': { en: 'Make Provocative',   ru: 'Сделать провокативным' },
    'btn.generate_prompt':  { en: 'Generate Prompt',    ru: 'Сгенерировать промпт' },

    // Stats
    'stat.total':           { en: 'Total Scripts',      ru: 'Всего скриптов' },
    'stat.published':       { en: 'Published',          ru: 'Опубликовано' },
    'stat.category':        { en: 'Category',           ru: 'Категория' },
    'stat.avg_score':       { en: 'Avg Viral Score',    ru: 'Средняя вирусность' },
    'stat.high':            { en: 'HIGH',               ru: 'ВЫСОКАЯ' },
    'stat.medium':          { en: 'MEDIUM',             ru: 'СРЕДНЯЯ' },
    'stat.low':             { en: 'LOW',                ru: 'НИЗКАЯ' },
    'stat.timeline':        { en: 'Publication Timeline', ru: 'Динамика публикаций' },

    // Tabs
    'tab.all':              { en: 'All',                ru: 'Все' },
    'tab.ai':               { en: 'AI',                 ru: 'AI' },
    'tab.finance':          { en: 'Finance',            ru: 'Финансы' },

    // Status options
    'status.ready':         { en: 'Ready',              ru: 'Готово' },
    'status.filmed':        { en: 'Filmed',             ru: 'Снято' },
    'status.published':     { en: 'Published',          ru: 'Опубликовано' },

    // Sections
    'sec.provocative':      { en: 'Provocative Version', ru: 'Провокативная версия' },
    'sec.video_prompt':     { en: 'Video Prompt',       ru: 'Видео промпт' },
    'sec.not_rewritten':    { en: '— not rewritten yet —', ru: '— ещё не переписано —' },
    'sec.original':         { en: 'Original Script',    ru: 'Оригинальный скрипт' },

    // Scripts Library
    'lib.title':            { en: 'Scripts Library',    ru: 'Библиотека скриптов' },
    'lib.subtitle':         { en: 'Unassigned scripts — assign to Boris, Daniel, or Thomas from script view', ru: 'Неназначенные скрипты — назначьте Борису, Дэниелу или Томасу из карточки скрипта' },
    'lib.no_scripts':       { en: 'No scripts yet.',    ru: 'Скриптов пока нет.' },
    'lib.search_link':      { en: 'Search for videos',  ru: 'Найти видео' },

    // Character pages
    'char.assigned':        { en: 'assigned scripts',   ru: 'назначенных скриптов' },
    'char.no_scripts':      { en: 'No scripts assigned yet.', ru: 'Скрипты ещё не назначены.' },
    'char.videos_by':       { en: 'videos by',          ru: 'видео от' },

    // Presets page
    'presets.title':        { en: 'Search Presets',     ru: 'Пресеты поиска' },
    'presets.subtitle':     { en: 'Manage preset search queries for quick access', ru: 'Управление пресетами поиска для быстрого доступа' },
    'presets.ai':           { en: 'AI Presets',         ru: 'AI пресеты' },
    'presets.finance':      { en: 'Finance Presets',    ru: 'Финансовые пресеты' },
    'presets.new_ai_ph':    { en: 'New AI preset query...', ru: 'Новый AI пресет...' },
    'presets.new_fin_ph':   { en: 'New finance preset query...', ru: 'Новый финансовый пресет...' },

    // Script view page
    'sv.back':              { en: 'Scripts Library',    ru: 'Библиотека скриптов' },
    'sv.character_type':    { en: 'Character Type',     ru: 'Тип персонажа' },
    'sv.assigned_to':       { en: 'Assigned To',        ru: 'Назначен' },
    'sv.production':        { en: 'Production Status',  ru: 'Статус продакшна' },
    'sv.publication':       { en: 'Publication',        ru: 'Публикация' },
    'sv.actions':           { en: 'Actions',            ru: 'Действия' },
    'sv.video_info':        { en: 'Video Info',         ru: 'Инфо о видео' },
    'sv.viral_potential':   { en: 'Viral Potential',    ru: 'Вирусный потенциал' },
    'sv.script_info':       { en: 'Script Info',        ru: 'Инфо о скрипте' },
    'sv.title_label':       { en: 'Title:',             ru: 'Название:' },
    'sv.url_label':         { en: 'URL:',               ru: 'Ссылка:' },
    'sv.search_query':      { en: 'Search query:',      ru: 'Поисковый запрос:' },
    'sv.category_label':    { en: 'Category:',          ru: 'Категория:' },
    'sv.score_label':       { en: 'Score:',             ru: 'Оценка:' },
    'sv.status_label':      { en: 'Status',             ru: 'Статус' },
    'sv.original_len':      { en: 'Original length',    ru: 'Длина оригинала' },
    'sv.created':           { en: 'Created',            ru: 'Создано' },
    'sv.not_classified':    { en: 'Not classified',     ru: 'Не классифицирован' },
    'sv.unassigned':        { en: 'Unassigned',         ru: 'Не назначен' },
    'sv.not_set':           { en: 'Not set',            ru: 'Не задан' },
    'sv.not_scored':        { en: 'Not scored',         ru: 'Не оценён' },
    'sv.modified':          { en: 'Modified',           ru: 'Изменён' },
    'sv.extracted':         { en: 'Extracted',          ru: 'Извлечён' },
    'sv.high_potential':    { en: 'HIGH POTENTIAL',     ru: 'ВЫСОКИЙ ПОТЕНЦИАЛ' },
    'sv.moderate':          { en: 'MODERATE',           ru: 'СРЕДНИЙ' },
    'sv.make_prov_ph':      { en: "Click 'Make Provocative' to generate...", ru: "Нажмите 'Сделать провокативным' для генерации..." },
    'sv.gen_prompt_ph':     { en: "Click 'Generate Prompt' to create a 2-part video storyboard...", ru: "Нажмите 'Сгенерировать промпт' для создания раскадровки..." },

    // Nari / Anna
    'nari.title':           { en: 'Sophia Alvares - Nari — Human', ru: 'Sophia Alvares - Nari — Human' },
    'anna.title':           { en: 'Ava - Anna',        ru: 'Ava - Anna' },

    // Search results
    'sr.back':              { en: 'Back to search',     ru: 'Назад к поиску' },
    'sr.videos_found':      { en: 'videos found',       ru: 'видео найдено' },
    'sr.no_results':        { en: 'No TikTok videos found for this query. Try a different search term.', ru: 'TikTok видео не найдены. Попробуйте другой запрос.' },
    'sr.view_script':       { en: 'View Script',        ru: 'Открыть скрипт' },
    'sr.extract':           { en: 'Extract Script',     ru: 'Извлечь скрипт' },

    // Avatars page
    'avatars.title':        { en: 'Avatar Gallery',     ru: 'Галерея аватаров' },
    'avatars.subtitle':     { en: 'AI avatars for Cinema Studio video generation', ru: 'AI аватары для генерации видео в Cinema Studio' },

    // Videos page
    'videos.title':         { en: 'All Videos',         ru: 'Все видео' },
    'videos.subtitle':      { en: 'Generated videos from Cinema Studio', ru: 'Сгенерированные видео из Cinema Studio' },

    // Settings page
    'settings.title':       { en: 'API Keys & Usage',   ru: 'API ключи и использование' },
    'settings.subtitle':    { en: 'Manage API keys and view usage statistics', ru: 'Управление API ключами и просмотр статистики использования' },
};

// --- Core functions ---

function i18nGetLang() {
    return localStorage.getItem('vs_lang') || 'en';
}

function i18nSetLang(lang) {
    localStorage.setItem('vs_lang', lang);
    i18nApply(lang);
    // Update toggle UI
    const toggle = document.getElementById('lang-toggle');
    if (toggle) {
        toggle.querySelectorAll('button').forEach(b => {
            b.classList.toggle('active', b.dataset.lang === lang);
        });
    }
}

function i18nApply(lang) {
    // Translate data-i18n elements (textContent)
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (I18N[key] && I18N[key][lang]) {
            el.textContent = I18N[key][lang];
        }
    });
    // Translate data-i18n-placeholder (input placeholder)
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (I18N[key] && I18N[key][lang]) {
            el.placeholder = I18N[key][lang];
        }
    });
    // Translate data-i18n-title (title attribute)
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (I18N[key] && I18N[key][lang]) {
            el.title = I18N[key][lang];
        }
    });
}

// Apply on load
document.addEventListener('DOMContentLoaded', function() {
    const lang = i18nGetLang();
    i18nApply(lang);
    // Set active toggle button
    const toggle = document.getElementById('lang-toggle');
    if (toggle) {
        toggle.querySelectorAll('button').forEach(b => {
            b.classList.toggle('active', b.dataset.lang === lang);
        });
    }
});
