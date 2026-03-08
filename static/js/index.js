const APP_CONFIG = window.APP_CONFIG || {};
const HISTORY_STORAGE_KEY = 'transcriptionHistory';
const UI_LANGUAGE_STORAGE_KEY = 'uiLanguage';
const HISTORY_LIMIT = 50;

const UI_LANGUAGE_META = {
    en: { flag: '🇬🇧' },
    ru: { flag: '🇷🇺' },
    es: { flag: '🇪🇸' },
    fr: { flag: '🇫🇷' },
    de: { flag: '🇩🇪' },
    zh: { flag: '🇨🇳' },
};

const ENGINE_META = {
    vosk: {
        titleKey: 'engines.vosk.title',
        descriptionKey: 'engines.vosk.description',
    },
    whisper: {
        titleKey: 'engines.whisper.title',
        descriptionKey: 'engines.whisper.description',
    },
};

const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const uploadBtn = document.getElementById('uploadBtn');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const uiLanguageMenu = document.getElementById('uiLanguageMenu');
const uiLanguageMenuToggle = document.getElementById('uiLanguageMenuToggle');
const uiLanguageMenuCurrent = document.getElementById('uiLanguageMenuCurrent');
const uiLanguageMenuDropdown = document.getElementById('uiLanguageMenuDropdown');
const uiLanguageOptions = document.getElementById('uiLanguageOptions');
const progress = document.getElementById('progress');
const results = document.getElementById('results');
const progressText = document.getElementById('progressText');
const progressDetails = document.getElementById('progressDetails');
const resultsSection = document.getElementById('resultsSection');
const uploadLimitBadge = document.getElementById('uploadLimitBadge');
const uploadHintText = document.getElementById('uploadHintText');
const engineOptions = document.getElementById('engineOptions');
const audioLanguageOptions = document.getElementById('audioLanguageOptions');
const healthBadge = document.getElementById('healthBadge');
const healthSummary = document.getElementById('healthSummary');
const localProcessingStatus = document.getElementById('localProcessingStatus');
const cloudRefinerStatus = document.getElementById('cloudRefinerStatus');
const whisperStatus = document.getElementById('whisperStatus');

let translations = {};
let selectedFiles = [];
let selectedEngine = APP_CONFIG.defaultEngine || 'vosk';
let selectedAudioLanguage = APP_CONFIG.defaultAudioLanguage || 'en';
let currentUiLanguage = 'en';
let latestHealthState = null;
let currentResultsView = [];
let isUiLanguageMenuOpen = false;

function hasUiLanguageMenu() {
    return Boolean(uiLanguageMenu && uiLanguageMenuToggle && uiLanguageMenuCurrent && uiLanguageMenuDropdown);
}

function hasLegacyUiLanguageOptions() {
    return Boolean(uiLanguageOptions);
}

function getNestedValue(target, path) {
    return path.split('.').reduce((value, segment) => value?.[segment], target);
}

function interpolate(template, variables = {}) {
    return Object.entries(variables).reduce((output, [key, value]) => {
        return output.replaceAll(`{${key}}`, String(value));
    }, template);
}

function t(key, variables = {}) {
    const rawValue = getNestedValue(translations, key);
    if (typeof rawValue !== 'string') {
        return key;
    }
    return interpolate(rawValue, variables);
}

function normalizeLanguageCode(code) {
    const supported = APP_CONFIG.supportedUiLanguages || Object.keys(UI_LANGUAGE_META);
    return supported.includes(code) ? code : APP_CONFIG.defaultUiLanguage || 'en';
}

function detectInitialUiLanguage() {
    const storedLanguage = localStorage.getItem(UI_LANGUAGE_STORAGE_KEY);
    if (storedLanguage) {
        return normalizeLanguageCode(storedLanguage);
    }

    const browserLanguage = (navigator.language || 'en').slice(0, 2).toLowerCase();
    return normalizeLanguageCode(browserLanguage);
}

function getAllowedExtensionsLabel() {
    return (APP_CONFIG.allowedExtensions || [])
        .map((extension) => `.${extension}`)
        .join(', ');
}

function getLanguageLabel(languageCode) {
    return t(`languages.${languageCode}`);
}

function getLanguageOptionTitle(languageCode) {
    const flag = UI_LANGUAGE_META[languageCode]?.flag || '🌐';
    return `${flag} ${getLanguageLabel(languageCode)}`;
}

function getEngineLabel(engineCode) {
    return t(ENGINE_META[engineCode]?.titleKey || engineCode);
}

function formatFileSize(bytes) {
    if (bytes === 0) {
        return '0 Bytes';
    }

    const units = ['Bytes', 'KB', 'MB', 'GB'];
    const sizeIndex = Math.floor(Math.log(bytes) / Math.log(1024));
    const sizeValue = Math.round((bytes / Math.pow(1024, sizeIndex)) * 100) / 100;
    return `${sizeValue} ${units[sizeIndex]}`;
}

function formatTimestamp(result) {
    const timestampIso = result.timestampIso || result.timestamp_iso;
    if (timestampIso) {
        return new Intl.DateTimeFormat(currentUiLanguage, {
            dateStyle: 'medium',
            timeStyle: 'short',
        }).format(new Date(timestampIso));
    }

    if (result.timestamp) {
        return result.timestamp;
    }

    return t('history.justNow');
}

function normalizeResult(result) {
    return {
        ...result,
        timestampIso: result.timestampIso || result.timestamp_iso || new Date().toISOString(),
        transcript_file: result.transcript_file || result.transcribed_file,
        transcript_display: result.transcript_display || result.transcribed_display,
    };
}

function getHistory() {
    try {
        const history = JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || '[]');
        return Array.isArray(history) ? history.map(normalizeResult) : [];
    } catch (error) {
        console.error('Error loading history:', error);
        return [];
    }
}

function saveToHistory(resultsData) {
    try {
        const nextResults = resultsData.map(normalizeResult);
        const history = [...nextResults, ...getHistory()].slice(0, HISTORY_LIMIT);
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
    } catch (error) {
        console.error('Error saving history:', error);
    }
}

function isWhisperAvailable() {
    return latestHealthState ? Boolean(latestHealthState.whisper_available) : true;
}

function isOpenAiConfigured() {
    return latestHealthState ? Boolean(latestHealthState.openai_configured) : true;
}

function isProcessingAllowed() {
    return isOpenAiConfigured() && (selectedEngine !== 'whisper' || isWhisperAvailable());
}

function updateUploadButtonState(isUploading = false) {
    uploadBtn.disabled = isUploading || selectedFiles.length === 0 || !isProcessingAllowed();
}

function setUploadingState(isUploading) {
    progress.classList.toggle('active', isUploading);
    updateUploadButtonState(isUploading);
}

function hideResultsSection() {
    resultsSection.hidden = true;
}

function ensureResultsVisible() {
    resultsSection.hidden = false;
}

function localizeError(payload) {
    const errorCode = payload?.error_code;
    const details = { ...(payload?.error_details || {}) };

    if (Array.isArray(details.allowed_extensions)) {
        details.allowed_extensions = details.allowed_extensions
            .map((extension) => (extension.startsWith('.') ? extension : `.${extension}`))
            .join(', ');
    }

    if (errorCode) {
        const translated = t(`errors.${errorCode}`, details);
        if (translated !== `errors.${errorCode}`) {
            return translated;
        }
    }

    return payload?.error || t('errors.generic');
}

function renderStaticTranslations() {
    document.title = t('meta.title');
    document.documentElement.lang = currentUiLanguage;

    document.querySelectorAll('[data-i18n]').forEach((element) => {
        element.textContent = t(element.dataset.i18n);
    });

    uploadLimitBadge.textContent = t('upload.limitBadge', {
        maxSizeMb: APP_CONFIG.maxContentLengthMb || 100,
    });
    uploadHintText.textContent = t('upload.hint', {
        extensions: getAllowedExtensionsLabel(),
        maxSizeMb: APP_CONFIG.maxContentLengthMb || 100,
    });

    if (!progress.classList.contains('active')) {
        progressText.textContent = t('progress.idleTitle');
        progressDetails.textContent = t('progress.idleDescription');
    }
}

function setUiLanguageMenuOpen(isOpen) {
    if (!hasUiLanguageMenu()) {
        return;
    }

    isUiLanguageMenuOpen = isOpen;
    uiLanguageMenuDropdown.hidden = !isOpen;
    uiLanguageMenuToggle.setAttribute('aria-expanded', String(isOpen));
}

function renderUiLanguageMenu() {
    if (!hasUiLanguageMenu()) {
        if (hasLegacyUiLanguageOptions()) {
            renderLegacyUiLanguageOptions();
        }
        return;
    }

    const flag = UI_LANGUAGE_META[currentUiLanguage]?.flag || '🌐';
    uiLanguageMenuCurrent.textContent = `${flag} ${getLanguageLabel(currentUiLanguage)}`;
    uiLanguageMenuDropdown.innerHTML = '';

    (APP_CONFIG.supportedUiLanguages || Object.keys(UI_LANGUAGE_META)).forEach((languageCode) => {
        const option = document.createElement('button');
        option.type = 'button';
        option.className = `language-menu-option${languageCode === currentUiLanguage ? ' is-active' : ''}`;
        option.dataset.languageCode = languageCode;
        option.innerHTML = `
            <span class="language-menu-option-main">
                <span>${UI_LANGUAGE_META[languageCode]?.flag || '🌐'}</span>
                <span>${getLanguageLabel(languageCode)}</span>
            </span>
            <span class="language-menu-option-code">${languageCode}</span>
        `;
        uiLanguageMenuDropdown.appendChild(option);
    });
}

function renderLegacyUiLanguageOptions() {
    if (!hasLegacyUiLanguageOptions()) {
        return;
    }

    uiLanguageOptions.innerHTML = '';
    (APP_CONFIG.supportedUiLanguages || Object.keys(UI_LANGUAGE_META)).forEach((languageCode) => {
        const title = getLanguageOptionTitle(languageCode);
        const description = languageCode.toUpperCase();
        uiLanguageOptions.appendChild(createChoiceCard({
            name: 'ui-language',
            value: languageCode,
            checked: languageCode === currentUiLanguage,
            title,
            description,
            onChange: (value) => {
                void setUiLanguage(value);
            },
        }));
    });
}

function createChoiceCard({ name, value, checked, title, description = '', disabled = false, onChange }) {
    const label = document.createElement('label');
    label.className = `choice-card${checked ? ' is-selected' : ''}${disabled ? ' is-disabled' : ''}`;

    const input = document.createElement('input');
    input.type = 'radio';
    input.name = name;
    input.value = value;
    input.checked = checked;
    input.disabled = disabled;
    input.addEventListener('change', () => onChange(value));

    const content = document.createElement('div');
    content.className = 'choice-content';

    const titleElement = document.createElement('div');
    titleElement.className = 'choice-title';
    titleElement.textContent = title;

    content.appendChild(titleElement);

    if (description) {
        const descriptionElement = document.createElement('div');
        descriptionElement.className = 'choice-description';
        descriptionElement.textContent = description;
        content.appendChild(descriptionElement);
    }

    label.appendChild(input);
    label.appendChild(content);
    return label;
}

function renderEngineOptions() {
    engineOptions.innerHTML = '';

    if (selectedEngine === 'whisper' && !isWhisperAvailable()) {
        selectedEngine = 'vosk';
    }

    (APP_CONFIG.supportedEngines || ['vosk', 'whisper']).forEach((engineCode) => {
        const isDisabled = engineCode === 'whisper' && !isWhisperAvailable();
        const description = isDisabled
            ? `${t(ENGINE_META[engineCode].descriptionKey)} ${t('health.whisperUnavailable')}.`
            : t(ENGINE_META[engineCode].descriptionKey);

        engineOptions.appendChild(createChoiceCard({
            name: 'engine',
            value: engineCode,
            checked: engineCode === selectedEngine,
            title: getEngineLabel(engineCode),
            description,
            disabled: isDisabled,
            onChange: (value) => {
                selectedEngine = value;
                renderEngineOptions();
                updateUploadButtonState();
            },
        }));
    });
}

function renderAudioLanguageOptions() {
    audioLanguageOptions.innerHTML = '';
    (APP_CONFIG.supportedAudioLanguages || []).forEach((languageCode) => {
        audioLanguageOptions.appendChild(createChoiceCard({
            name: 'audio-language',
            value: languageCode,
            checked: languageCode === selectedAudioLanguage,
            title: getLanguageOptionTitle(languageCode),
            description: languageCode.toUpperCase(),
            onChange: (value) => {
                selectedAudioLanguage = value;
                renderAudioLanguageOptions();
            },
        }));
    });
}

function renderFileList() {
    fileList.innerHTML = '';

    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span class="file-name">${file.name} (${formatFileSize(file.size)})</span>
            <button class="file-remove" type="button" data-remove-index="${index}">
                ${t('actions.removeFile')}
            </button>
        `;
        fileList.appendChild(fileItem);
    });
}

function handleFiles(files) {
    selectedFiles = Array.from(files);
    renderFileList();
    updateUploadButtonState();
}

function resetSelectedFiles() {
    selectedFiles = [];
    fileInput.value = '';
    renderFileList();
    updateUploadButtonState();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
    updateUploadButtonState();
}

function createMetaChip(label, value) {
    return `
        <span class="meta-chip">
            <strong>${label}:</strong>
            <span>${value}</span>
        </span>
    `;
}

function createResultMarkup(inputResult) {
    const result = normalizeResult(inputResult);
    const metaChips = [
        createMetaChip(t('history.processedAt'), formatTimestamp(result)),
    ];

    if (result.engine) {
        metaChips.push(createMetaChip(t('history.engine'), getEngineLabel(result.engine)));
    }

    if (result.language) {
        metaChips.push(createMetaChip(t('history.audioLanguage'), getLanguageLabel(result.language)));
    }

    let content = `
        <div class="result-filename">${result.filename}</div>
        <div class="result-meta">${metaChips.join('')}</div>
    `;

    if (result.status === 'success') {
        const transcriptDisplay = result.transcript_display || result.transcript_file;
        const refinedDisplay = result.refined_display || result.refined_file;

        content += `
            <div class="result-status success">${t('history.success')}</div>
            <div class="download-links">
                <a href="/download/${encodeURIComponent(result.transcript_file)}" class="btn btn-download" download="${transcriptDisplay}">
                    ${t('history.downloadTranscript')}
                </a>
                <a href="/download/${encodeURIComponent(result.refined_file)}" class="btn btn-download" download="${refinedDisplay}">
                    ${t('history.downloadRefined')}
                </a>
            </div>
        `;
    } else {
        content += `
            <div class="result-status error">${t('history.errorLabel')}</div>
            <div class="panel-description">${localizeError(result)}</div>
        `;
    }

    return content;
}

function createResultElement(result) {
    const resultItem = document.createElement('div');
    resultItem.className = `result-item ${result.status}`;
    resultItem.innerHTML = createResultMarkup(result);
    return resultItem;
}

function displayResults(resultsData) {
    currentResultsView = resultsData.map(normalizeResult);
    results.innerHTML = '';

    if (currentResultsView.length === 0) {
        hideResultsSection();
        return;
    }

    ensureResultsVisible();
    currentResultsView.forEach((result) => {
        results.appendChild(createResultElement(result));
    });
}

function addSingleResult(result) {
    const normalizedResult = normalizeResult(result);
    currentResultsView = [normalizedResult, ...currentResultsView];
    ensureResultsVisible();
    results.insertBefore(createResultElement(normalizedResult), results.firstChild);
}

function showGeneralError(payloadOrMessage) {
    const message = typeof payloadOrMessage === 'string'
        ? payloadOrMessage
        : localizeError(payloadOrMessage);

    ensureResultsVisible();
    currentResultsView = [];
    results.innerHTML = `
        <div class="result-item error">
            <div class="result-filename">${t('history.errorLabel')}</div>
            <div class="panel-description">${message}</div>
        </div>
    `;
}

function clearHistory() {
    if (confirm(t('actions.confirmClearHistory'))) {
        localStorage.removeItem(HISTORY_STORAGE_KEY);
        currentResultsView = [];
        results.innerHTML = '';
        hideResultsSection();
    }
}

function finishUpload(currentResults) {
    setUploadingState(false);
    saveToHistory(currentResults);
    resetSelectedFiles();
}

function updateProgressDetails(processedCount, totalFiles, engine, language) {
    progressDetails.textContent = t('progress.details', {
        processedCount,
        totalFiles,
        engine: getEngineLabel(engine),
        language: getLanguageLabel(language),
    });
}

function processEventData(data, context) {
    if (data.done) {
        finishUpload(context.currentResults);
        return;
    }

    if (data.status === 'success' || data.status === 'error') {
        const normalizedResult = normalizeResult(data);
        context.processedCount += 1;
        context.currentResults.push(normalizedResult);
        addSingleResult(normalizedResult);
        updateProgressDetails(
            context.processedCount,
            context.totalFiles,
            context.engine,
            context.language
        );
        return;
    }

    if (data.error) {
        showGeneralError(data);
        setUploadingState(false);
    }
}

function handleSseChunk(chunk, context) {
    const events = chunk.split('\n\n');
    const incompleteEvent = events.pop() || '';

    events.forEach((eventBlock) => {
        const dataLine = eventBlock
            .split('\n')
            .find((line) => line.startsWith('data: '));

        if (!dataLine) {
            return;
        }

        try {
            const data = JSON.parse(dataLine.substring(6));
            processEventData(data, context);
        } catch (error) {
            console.error('Error parsing SSE data:', error);
        }
    });

    return incompleteEvent;
}

function renderHealthPanel() {
    const health = latestHealthState;
    const healthStatus = health?.status || 'warning';
    healthBadge.className = `status-chip ${healthStatus}`;
    healthBadge.textContent = t(`health.badges.${healthStatus}`);

    if (!health) {
        healthSummary.textContent = t('status.loading');
        localProcessingStatus.textContent = t('health.localReady');
        cloudRefinerStatus.textContent = t('health.loading');
        whisperStatus.textContent = t('health.loading');
        return;
    }

    if (health.status === 'ok' && health.openai_configured) {
        healthSummary.textContent = t('health.summary.ready');
    } else if (health.status === 'warning' && !health.openai_configured) {
        healthSummary.textContent = t('health.summary.openaiMissing');
    } else {
        healthSummary.textContent = t('health.summary.degraded');
    }

    localProcessingStatus.textContent = t('health.localReady');
    cloudRefinerStatus.textContent = health.openai_configured
        ? t('health.openaiConfigured')
        : t('health.openaiMissing');
    whisperStatus.textContent = health.whisper_available
        ? t('health.whisperAvailable')
        : t('health.whisperUnavailable');

    renderEngineOptions();
    updateUploadButtonState();
}

async function loadHealth() {
    try {
        const response = await fetch('/health', { cache: 'no-store' });
        latestHealthState = await response.json();
    } catch (error) {
        latestHealthState = {
            status: 'error',
            openai_configured: false,
            whisper_available: false,
        };
    }

    renderHealthPanel();
}

async function loadTranslations(languageCode) {
    const response = await fetch(`/static/i18n/${languageCode}.json`, { cache: 'no-store' });
    if (!response.ok) {
        throw new Error(`Failed to load translations for ${languageCode}`);
    }
    return response.json();
}

async function setUiLanguage(languageCode) {
    const normalizedLanguage = normalizeLanguageCode(languageCode);
    translations = await loadTranslations(normalizedLanguage);
    currentUiLanguage = normalizedLanguage;
    localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, normalizedLanguage);

    renderStaticTranslations();
    renderUiLanguageMenu();
    renderLegacyUiLanguageOptions();
    setUiLanguageMenuOpen(false);
    renderEngineOptions();
    renderAudioLanguageOptions();
    renderFileList();
    displayResults(currentResultsView.length > 0 ? currentResultsView : getHistory());
    renderHealthPanel();
}

function uploadSelectedFiles() {
    if (selectedFiles.length === 0) {
        return;
    }

    const totalFiles = selectedFiles.length;
    const context = {
        currentResults: [],
        totalFiles,
        engine: selectedEngine,
        language: selectedAudioLanguage,
        processedCount: 0,
    };

    progressText.textContent = t(
        totalFiles === 1 ? 'progress.processingSingle' : 'progress.processingMultiple',
        { count: totalFiles }
    );
    updateProgressDetails(0, totalFiles, selectedEngine, selectedAudioLanguage);
    setUploadingState(true);

    const formData = new FormData();
    selectedFiles.forEach((file) => {
        formData.append('files[]', file);
    });
    formData.append('engine', selectedEngine);
    formData.append('language', selectedAudioLanguage);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);

    let processedLength = 0;
    let pendingBuffer = '';

    xhr.onprogress = function onProgress() {
        const newChunk = xhr.responseText.substring(processedLength);
        processedLength = xhr.responseText.length;
        pendingBuffer += newChunk;
        pendingBuffer = handleSseChunk(pendingBuffer, context);
    };

    xhr.onload = function onLoad() {
        if (xhr.status >= 400) {
            try {
                const errorPayload = JSON.parse(xhr.responseText);
                showGeneralError(errorPayload);
            } catch (error) {
                showGeneralError(t('errors.generic'));
            }
            setUploadingState(false);
        }
    };

    xhr.onerror = function onError() {
        showGeneralError(t('errors.connection'));
        setUploadingState(false);
    };

    xhr.send(formData);
}

function attachEventListeners() {
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });

    if (hasUiLanguageMenu()) {
        uiLanguageMenuToggle.addEventListener('click', () => {
            setUiLanguageMenuOpen(!isUiLanguageMenuOpen);
        });

        uiLanguageMenuDropdown.addEventListener('click', (event) => {
            const option = event.target.closest('[data-language-code]');
            if (!option) {
                return;
            }

            void setUiLanguage(option.dataset.languageCode);
        });
    }

    fileInput.addEventListener('change', (event) => {
        handleFiles(event.target.files);
    });

    uploadArea.addEventListener('dragover', (event) => {
        event.preventDefault();
        uploadArea.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', (event) => {
        event.preventDefault();
        uploadArea.classList.remove('drag-over');
        handleFiles(event.dataTransfer.files);
    });

    fileList.addEventListener('click', (event) => {
        const button = event.target.closest('[data-remove-index]');
        if (!button) {
            return;
        }

        removeFile(Number(button.dataset.removeIndex));
    });

    uploadBtn.addEventListener('click', uploadSelectedFiles);
    clearHistoryBtn.addEventListener('click', clearHistory);

    if (hasUiLanguageMenu()) {
        document.addEventListener('click', (event) => {
            if (!uiLanguageMenu.contains(event.target)) {
                setUiLanguageMenuOpen(false);
            }
        });
    }
}

async function initializeApp() {
    try {
        currentUiLanguage = detectInitialUiLanguage();
        await setUiLanguage(currentUiLanguage);
        displayResults(getHistory());
        updateUploadButtonState();
        await loadHealth();
        attachEventListeners();
    } catch (error) {
        console.error('Initialization error:', error);
        showGeneralError('Failed to initialize the interface.');
    }
}

void initializeApp();
