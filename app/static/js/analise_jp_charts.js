const ctx = window.__ANALISE_JP__ || {};

const state = {
    charts: Array.isArray(ctx.charts) ? [...ctx.charts] : [],
    datasets: new Map(),
    datasetPromises: new Map(),
    pendingDelete: null,
    selectAllActive: false,
    currentViewId: null,
    viewRenderToken: 0,
    chartCards: new Map(),
    lazyObserver: null,
    pendingRenders: new Set(),
    prefetchedCategories: new Set(),
    previewResizeHandler: null,
    renderVersion: 0
};

const chartInstances = new Map();
const viewChartInstances = new Map();

const CHART_TYPE_LABELS = {
    bar: 'Barras verticais',
    horizontal_bar: 'Barras horizontais',
    line: 'Linha',
    pie: 'Pizza',
    doughnut: 'Rosquinha',
    radar: 'Radar'
};

const elements = {
    chartsGrid: document.getElementById('chartsGrid'),
    chartsEmptyState: document.getElementById('chartsEmptyState'),
    chartsSubtitle: document.getElementById('chartsSubtitle'),
    openModalBtn: document.getElementById('openCreateChartBtn'),
    emptyStateCreateBtn: document.getElementById('emptyStateCreateBtn'),
    refreshBtn: document.getElementById('refreshChartsBtn'),
    chartModal: document.getElementById('chartModal'),
    chartModalOverlay: document.getElementById('chartModalOverlay'),
    closeModalBtn: document.getElementById('closeChartModalBtn'),
    cancelModalBtn: document.getElementById('cancelChartBtn'),
    chartForm: document.getElementById('chartForm'),
    chartTitle: document.getElementById('chartTitle'),
    chartType: document.getElementById('chartType'),
    chartCategory: document.getElementById('chartCategory'),
    categoryHint: document.getElementById('categoryHint'),
    dimensionField: document.getElementById('dimensionField'),
    valueFieldOptions: document.getElementById('valueFieldOptions'),
    valueFieldEmpty: document.getElementById('valueFieldEmpty'),
    fieldLoadingState: document.getElementById('fieldLoadingState'),
    toggleSelectAllValues: document.getElementById('toggleSelectAllValues'),
    formFeedback: document.getElementById('chartFormFeedback'),
    submitBtn: document.getElementById('submitChartBtn'),
    submitSpinner: document.getElementById('submitChartSpinner'),
    toastContainer: document.getElementById('toastContainer'),
    deleteModal: document.getElementById('deleteModal'),
    deleteModalOverlay: document.getElementById('deleteModalOverlay'),
    deleteMessage: document.getElementById('deleteModalMessage'),
    confirmDeleteBtn: document.getElementById('confirmDeleteBtn'),
    deleteSpinner: document.getElementById('deleteSpinner'),
    cancelDeleteBtn: document.getElementById('cancelDeleteBtn'),
    closeDeleteModalBtn: document.getElementById('closeDeleteModalBtn'),
    viewModal: document.getElementById('viewChartModal'),
    viewModalOverlay: document.getElementById('viewChartModalOverlay'),
    closeViewModalBtn: document.getElementById('closeViewChartBtn'),
    nextViewModalBtn: document.getElementById('nextViewChartBtn'),
    viewChartTitle: document.getElementById('viewChartTitle'),
    viewChartMeta: document.getElementById('viewChartMeta'),
    viewChartCanvas: document.getElementById('viewChartCanvas'),
    viewChartMessage: document.getElementById('viewChartMessage')
};

const DEFAULT_PALETTE = ['#38BDF8', '#22D3EE', '#A855F7', '#F97316', '#FACC15', '#34D399'];

function createThrottled(fn, delay = 120) {
    let timeoutId = null;
    let lastArgs = null;
    return function throttled(...args) {
        lastArgs = args;
        if (timeoutId) {
            return;
        }
        timeoutId = setTimeout(() => {
            timeoutId = null;
            fn.apply(this, lastArgs);
        }, delay);
    };
}

function scheduleIdle(work, timeout = 150) {
    if (typeof window !== 'undefined' && typeof window.requestIdleCallback === 'function') {
        window.requestIdleCallback(work, { timeout });
    } else {
        setTimeout(work, Math.min(timeout, 120));
    }
}

function bumpRenderVersion() {
    state.renderVersion += 1;
}

function slugToLabel(slug) {
    if (!slug) return '';
    return slug
        .split('_')
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ');
}

function getChartTypeLabel(type) {
    if (!type) return '';
    return CHART_TYPE_LABELS[type] || slugToLabel(type.replace('polararea', 'polar_area'));
}

function getPalette() {
    if (Array.isArray(ctx.themePalette) && ctx.themePalette.length) {
        return ctx.themePalette;
    }
    return DEFAULT_PALETTE;
}

function getChartJsType(chartType) {
    if (!chartType) return 'bar';
    return chartType === 'horizontal_bar' ? 'bar' : chartType;
}

function isHorizontalBar(chartType) {
    return chartType === 'horizontal_bar';
}

function showToast(message, type = 'success') {
    if (!elements.toastContainer) return;
    const toast = document.createElement('div');
    const baseClass = 'glass-panel border border-white/10 rounded-2xl px-4 py-3 text-sm shadow-lg flex items-center gap-3';
    const themeClass = type === 'error'
        ? (ctx.themeClasses?.toastError || 'bg-rose-600 text-white')
        : (ctx.themeClasses?.toastSuccess || 'bg-emerald-600 text-white');
    toast.className = `${baseClass} ${themeClass}`;
    toast.textContent = message;
    elements.toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 220);
    }, 3200);
}

function setFormFeedback(message) {
    if (!elements.formFeedback) return;
    if (!message) {
        elements.formFeedback.classList.add('hidden');
        elements.formFeedback.textContent = '';
        return;
    }
    elements.formFeedback.textContent = message;
    elements.formFeedback.classList.remove('hidden');
}

function setSubmitLoading(isLoading) {
    if (!elements.submitBtn) return;
    elements.submitBtn.disabled = isLoading;
    if (elements.submitSpinner) {
        elements.submitSpinner.classList.toggle('hidden', !isLoading);
    }
}

function setDeleteLoading(isLoading) {
    if (!elements.confirmDeleteBtn) return;
    elements.confirmDeleteBtn.disabled = isLoading;
    if (elements.deleteSpinner) {
        elements.deleteSpinner.classList.toggle('hidden', !isLoading);
    }
}

function closeModal() {
    if (!elements.chartModal) return;
    elements.chartModal.classList.add('hidden');
    setFormFeedback('');
    state.selectAllActive = false;
}

function openModal() {
    if (!elements.chartModal) return;
    populateChartTypes();
    populateCategorySelect();
    elements.chartTitle.value = '';
    setFormFeedback('');
    setSubmitLoading(false);
    const firstAvailable = Array.from(elements.chartCategory.options).find((option) => !option.disabled && option.value);
    if (firstAvailable) {
        elements.chartCategory.value = firstAvailable.value;
        updateCategoryHint(firstAvailable.value);
        loadFieldsForCategory(firstAvailable.value);
    } else {
        elements.chartCategory.value = '';
        updateCategoryHint('');
        clearFieldSelectors();
    }
    elements.chartModal.classList.remove('hidden');
}

function openDeleteModal(chart) {
    if (!elements.deleteModal) return;
    state.pendingDelete = chart?.id || null;
    if (elements.deleteMessage) {
        elements.deleteMessage.textContent = chart?.nome
            ? `Tem certeza que deseja remover o gráfico "${chart.nome}"?`
            : 'Tem certeza que deseja remover este gráfico?';
    }
    setDeleteLoading(false);
    elements.deleteModal.classList.remove('hidden');
}

function closeDeleteModal() {
    if (!elements.deleteModal) return;
    state.pendingDelete = null;
    setDeleteLoading(false);
    elements.deleteModal.classList.add('hidden');
}

function populateChartTypes() {
    if (!elements.chartType) return;
    elements.chartType.innerHTML = '';
    const types = Array.isArray(ctx.allowedChartTypes) && ctx.allowedChartTypes.length
        ? ctx.allowedChartTypes
        : ['bar', 'line', 'pie', 'doughnut', 'radar'];
    types.forEach((type) => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = getChartTypeLabel(type);
        elements.chartType.appendChild(option);
    });
}

function populateCategorySelect() {
    if (!elements.chartCategory) return;
    elements.chartCategory.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Selecione uma categoria';
    placeholder.disabled = true;
    placeholder.selected = true;
    elements.chartCategory.appendChild(placeholder);

    const categories = Array.isArray(ctx.categories) ? ctx.categories : [];
    categories.forEach((category) => {
        const option = document.createElement('option');
        option.value = category.slug;
        option.textContent = category.label || slugToLabel(category.slug);
        if (!category.has_data) {
            option.disabled = true;
            option.textContent += ' • sem dados';
        }
        elements.chartCategory.appendChild(option);
    });
}

function updateCategoryHint(slug) {
    if (!elements.categoryHint) return;
    const categories = Array.isArray(ctx.categories) ? ctx.categories : [];
    const entry = categories.find((item) => item.slug === slug);
    if (!entry) {
        elements.categoryHint.textContent = '';
        return;
    }
    if (!entry.has_data) {
        elements.categoryHint.textContent = 'Nenhum upload disponível para esta categoria.';
        return;
    }
    if (entry.latest_upload?.nome_arquivo) {
        const uploadedAt = entry.latest_upload.created_at
            ? new Date(entry.latest_upload.created_at).toLocaleString('pt-BR')
            : '';
        elements.categoryHint.textContent = uploadedAt
            ? `Último upload: ${entry.latest_upload.nome_arquivo} em ${uploadedAt}`
            : `Último upload: ${entry.latest_upload.nome_arquivo}`;
    } else {
        elements.categoryHint.textContent = 'Dados disponíveis para criar gráficos.';
    }
}

function clearFieldSelectors() {
    if (elements.dimensionField) {
        elements.dimensionField.innerHTML = '<option value="">Selecione uma categoria</option>';
        elements.dimensionField.disabled = true;
    }
    if (elements.valueFieldOptions) {
        elements.valueFieldOptions.innerHTML = '';
    }
    if (elements.valueFieldEmpty) {
        elements.valueFieldEmpty.classList.add('hidden');
    }
    if (elements.toggleSelectAllValues) {
        elements.toggleSelectAllValues.classList.add('hidden');
    }
}

function setFieldLoading(isLoading) {
    if (elements.fieldLoadingState) {
        elements.fieldLoadingState.classList.toggle('hidden', !isLoading);
    }
}

function buildDatasetUrl(category) {
    let endpoint = ctx.endpoints?.dataset || '';
    if (!endpoint) return '';
    return endpoint.replace('__categoria__', encodeURIComponent(category));
}

async function fetchDataset(category, { force = false } = {}) {
    if (!category) return null;
    if (force) {
        state.datasets.delete(category);
        state.datasetPromises.delete(category);
    } else {
        if (state.datasets.has(category)) {
            return state.datasets.get(category);
        }
        if (state.datasetPromises.has(category)) {
            return state.datasetPromises.get(category);
        }
    }

    const url = buildDatasetUrl(category);
    if (!url) return null;

    const request = (async () => {
        const response = await fetch(url);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data?.error || 'Falha ao carregar dados da categoria.');
        }
        state.datasets.set(category, data);
        return data;
    })();

    state.datasetPromises.set(category, request);
    try {
        return await request;
    } finally {
        state.datasetPromises.delete(category);
    }
}

function createValueCheckbox(field, index, defaults = []) {
    const wrapper = document.createElement('label');
    wrapper.className = 'flex items-center gap-3 rounded-xl px-3 py-2 hover:bg-white/10 transition-colors cursor-pointer';

    const input = document.createElement('input');
    input.type = 'checkbox';
    input.value = field;
    input.checked = defaults.includes(field);
    input.className = 'h-4 w-4 rounded border-white/20 bg-transparent';

    const name = document.createElement('span');
    name.className = 'text-sm text-white/80 truncate';
    name.textContent = field;

    wrapper.appendChild(input);
    wrapper.appendChild(name);
    return wrapper;
}

function detectDefaultValues(fields, dimension) {
    const filtered = fields.filter((field) => field !== dimension);
    return filtered.slice(0, 2);
}

async function loadFieldsForCategory(category) {
    clearFieldSelectors();
    if (!category) return;
    setFieldLoading(true);
    try {
        const dataset = await fetchDataset(category);
        const fields = Array.isArray(dataset?.fields) ? dataset.fields : [];
        const records = Array.isArray(dataset?.records) ? dataset.records : [];

        if (!fields.length || !records.length) {
            if (elements.valueFieldEmpty) {
                elements.valueFieldEmpty.classList.remove('hidden');
                elements.valueFieldEmpty.textContent = 'Nenhum dado disponível para esta categoria.';
            }
            return;
        }

        if (elements.dimensionField) {
            elements.dimensionField.disabled = false;
            elements.dimensionField.innerHTML = '';
            fields.forEach((field, index) => {
                const option = document.createElement('option');
                option.value = field;
                option.textContent = field;
                if (index === 0) {
                    option.selected = true;
                }
                elements.dimensionField.appendChild(option);
            });
        }

        const defaults = detectDefaultValues(fields, elements.dimensionField?.value || fields[0]);
        if (elements.valueFieldOptions) {
            elements.valueFieldOptions.innerHTML = '';
            fields.forEach((field, index) => {
                const checkbox = createValueCheckbox(field, index, defaults);
                elements.valueFieldOptions.appendChild(checkbox);
            });
        }

        if (elements.toggleSelectAllValues) {
            elements.toggleSelectAllValues.classList.toggle('hidden', !fields.length);
            elements.toggleSelectAllValues.textContent = 'Selecionar todos';
            state.selectAllActive = false;
        }

        if (elements.valueFieldEmpty) {
            elements.valueFieldEmpty.classList.toggle('hidden', !!fields.length);
        }
    } catch (error) {
        setFormFeedback(error.message);
        clearFieldSelectors();
    } finally {
        setFieldLoading(false);
    }
}

function getSelectedValueFields() {
    if (!elements.valueFieldOptions) return [];
    return Array.from(elements.valueFieldOptions.querySelectorAll('input[type="checkbox"]:checked'))
        .map((input) => input.value)
        .filter(Boolean);
}

function toggleSelectAllValues() {
    if (!elements.valueFieldOptions) return;
    const checkboxes = Array.from(elements.valueFieldOptions.querySelectorAll('input[type="checkbox"]'));
    if (!checkboxes.length) return;
    const shouldSelectAll = !state.selectAllActive;
    checkboxes.forEach((checkbox) => {
        checkbox.checked = shouldSelectAll;
    });
    state.selectAllActive = shouldSelectAll;
    if (elements.toggleSelectAllValues) {
        elements.toggleSelectAllValues.textContent = shouldSelectAll ? 'Limpar seleção' : 'Selecionar todos';
    }
}

function buildDeleteUrl(chartId) {
    const template = ctx.endpoints?.delete || '';
    if (!template) return '';
    if (template.endsWith('/0')) {
        return `${template.slice(0, -1)}${chartId}`;
    }
    if (template.includes('/0/')) {
        return template.replace('/0/', `/${chartId}/`);
    }
    return template.replace(/0$/, String(chartId));
}

function parseNumeric(value) {
    if (typeof value === 'number') {
        return Number.isFinite(value) ? value : null;
    }
    if (typeof value !== 'string') return null;
    const trimmed = value.trim();
    if (!trimmed) return null;
    const timeMatch = trimmed.match(/^([+-]?)(\d+):([0-5]?\d)(?::([0-5]?\d))?$/);
    if (timeMatch) {
        const sign = timeMatch[1] === '-' ? -1 : 1;
        const hours = parseInt(timeMatch[2], 10);
        const minutes = parseInt(timeMatch[3], 10);
        const seconds = timeMatch[4] ? parseInt(timeMatch[4], 10) : 0;
        const decimalHours = hours + minutes / 60 + seconds / 3600;
        return sign * decimalHours;
    }
    let normalized = trimmed.replace(/\s+/g, '');
    if (normalized.includes(',') && normalized.includes('.')) {
        normalized = normalized.replace(/\./g, '').replace(',', '.');
    } else if (normalized.includes(',')) {
        normalized = normalized.replace(',', '.');
    }
    const numeric = Number(normalized);
    return Number.isFinite(numeric) ? numeric : null;
}

function prepareChartData(records, dimensionField, valueFields) {
    const labels = [];
    const fields = Array.isArray(valueFields) ? valueFields : [];
    const series = fields.map(() => []);
    records.forEach((record) => {
        if (!record || typeof record !== 'object') return;
        const label = record[dimensionField];
        if (label === undefined || label === null || label === '') return;
        labels.push(String(label));
        fields.forEach((field, index) => {
            const value = parseNumeric(record[field]);
            series[index].push(value);
        });
    });
    return { labels, series };
}

function hexToRgba(hex, alpha = 1) {
    if (!hex) return `rgba(56, 189, 248, ${alpha})`;
    const sanitized = hex.replace('#', '');
    if (sanitized.length !== 6) {
        return `rgba(56, 189, 248, ${alpha})`;
    }
    const bigint = parseInt(sanitized, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function buildDatasets(chart, labels, series) {
    const palette = Array.isArray(chart.options?.colors) && chart.options.colors.length
        ? chart.options.colors
        : getPalette();
    const type = getChartJsType(chart.chart_type);
    const valueFields = Array.isArray(chart.value_fields) ? chart.value_fields : [];

    return valueFields.map((field, index) => {
        const baseColor = palette[index % palette.length];
        if (type === 'pie' || type === 'doughnut') {
            const background = labels.map((_, labelIndex) => palette[(index + labelIndex) % palette.length]);
            return {
                label: field,
                data: series[index],
                backgroundColor: background,
                borderWidth: 1,
                borderColor: hexToRgba('#ffffff', 0.08)
            };
        }

        if (type === 'radar') {
            return {
                label: field,
                data: series[index],
                fill: true,
                backgroundColor: hexToRgba(baseColor, 0.25),
                borderColor: baseColor,
                pointBackgroundColor: baseColor,
                pointBorderColor: '#fff',
                pointHoverBorderColor: baseColor,
                borderWidth: 2
            };
        }

        return {
            label: field,
            data: series[index],
            borderColor: baseColor,
            backgroundColor: type === 'bar' ? hexToRgba(baseColor, 0.55) : hexToRgba(baseColor, 0.15),
            borderWidth: 2,
            tension: 0.35,
            fill: type !== 'bar'
        };
    });
}


function drawChart(chart, canvas, messageEl, labels, series, instanceStore, options = {}) {
    const { disableAnimation = false } = options;
    const hasValues = series.some((values) => values.some((value) => typeof value === 'number'));
    if (!labels.length || !hasValues) {
        if (messageEl) {
            messageEl.classList.remove('hidden');
            messageEl.textContent = 'Não há dados numéricos suficientes para renderizar este gráfico.';
        }
        canvas.classList.add('hidden');
        if (instanceStore && typeof instanceStore.has === 'function' && instanceStore.has(chart.id)) {
            const existing = instanceStore.get(chart.id);
            if (existing && typeof existing.destroy === 'function') {
                existing.destroy();
            }
            instanceStore.delete(chart.id);
        }
        return null;
    }

    if (messageEl) {
        messageEl.classList.add('hidden');
        messageEl.textContent = '';
    }
    canvas.classList.remove('hidden');

    const datasets = buildDatasets(chart, labels, series);
    const context = canvas.getContext('2d');
    if (!context) {
        return null;
    }

    const chartJsType = getChartJsType(chart.chart_type);
    const horizontalBar = isHorizontalBar(chart.chart_type);
    const isCircular = chartJsType === 'pie' || chartJsType === 'doughnut';
    const isRadar = chartJsType === 'radar';

    const axisTickColor = 'rgba(226, 232, 240, 0.7)';
    const axisGridColor = 'rgba(148, 163, 184, 0.15)';

    const scales = (() => {
        if (isCircular) {
            return {};
        }
        if (isRadar) {
            return {
                r: {
                    angleLines: { color: axisGridColor },
                    grid: { color: axisGridColor },
                    pointLabels: { color: axisTickColor },
                    ticks: { color: axisTickColor }
                }
            };
        }

        const createAxis = () => ({
            ticks: { color: axisTickColor },
            grid: { color: axisGridColor }
        });

        return horizontalBar
            ? { x: createAxis(), y: createAxis() }
            : { x: createAxis(), y: createAxis() };
    })();

    const plugins = {
        legend: {
            position: 'bottom',
            labels: {
                color: 'rgba(226, 232, 240, 0.85)',
                padding: 14,
                usePointStyle: true
            }
        },
        tooltip: {
            mode: 'index',
            intersect: false
        }
    };

    if (instanceStore && typeof instanceStore.has === 'function' && instanceStore.has(chart.id)) {
        const existing = instanceStore.get(chart.id);
        if (existing) {
            if (existing.config?.type === chartJsType) {
                existing.data.labels = labels;
                existing.data.datasets = datasets;
                existing.options.indexAxis = horizontalBar ? 'y' : 'x';
                existing.options.scales = scales;
                existing.options.plugins = { ...existing.options.plugins, ...plugins };
                existing.options.animation = disableAnimation ? false : { duration: 420, easing: 'easeOutQuart' };
                existing.update(disableAnimation ? 'none' : undefined);
                return existing;
            }
            if (typeof existing.destroy === 'function') {
                existing.destroy();
            }
        }
        instanceStore.delete(chart.id);
    }

    const instance = new Chart(context, {
        type: chartJsType,
        data: {
            labels,
            datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: horizontalBar ? 'y' : 'x',
            animation: disableAnimation ? false : { duration: 420, easing: 'easeOutQuart' },
            plugins,
            scales
        }
    });

    if (instanceStore && typeof instanceStore.set === 'function') {
        instanceStore.set(chart.id, instance);
    }

    return instance;
}

function renderChartInstance(chart, canvas, messageEl, options = {}) {
    if (!canvas) return Promise.resolve(null);
    const {
        instanceStore = chartInstances,
        disableAnimation = false,
        keepMessage = false
    } = options;
    const category = chart.categoria;

    if (!keepMessage && messageEl) {
        messageEl.classList.add('hidden');
        messageEl.textContent = '';
    }
    if (keepMessage) {
        canvas.classList.add('hidden');
    } else {
        canvas.classList.remove('hidden');
    }

    return fetchDataset(category)
        .then((dataset) => {
            const records = Array.isArray(dataset?.records) ? dataset.records : [];
            const valueFields = Array.isArray(chart.value_fields) ? chart.value_fields : [];
            const { labels, series } = prepareChartData(records, chart.dimension_field, valueFields);
            const instance = drawChart(
                { ...chart, value_fields: valueFields },
                canvas,
                messageEl,
                labels,
                series,
                instanceStore,
                { disableAnimation }
            );
            if (instance) {
                canvas.classList.remove('hidden');
                if (messageEl) {
                    messageEl.classList.add('hidden');
                    messageEl.textContent = '';
                }
            }
            return instance;
        })
        .catch((error) => {
            if (messageEl) {
                messageEl.classList.remove('hidden');
                messageEl.textContent = error.message || 'Falha ao carregar dados do gráfico.';
            }
            canvas.classList.add('hidden');
            if (instanceStore && typeof instanceStore.has === 'function' && instanceStore.has(chart.id)) {
                const existing = instanceStore.get(chart.id);
                if (existing && typeof existing.destroy === 'function') {
                    existing.destroy();
                }
                instanceStore.delete(chart.id);
            }
            return null;
        });
}


function computeChartSignature(chart) {
    return JSON.stringify({
        id: chart.id,
        nome: chart.nome,
        chartType: chart.chart_type,
        categoria: chart.categoria,
        dimension: chart.dimension_field,
        valueFields: Array.isArray(chart.value_fields) ? chart.value_fields : [],
        colors: Array.isArray(chart.options?.colors) ? chart.options.colors : [],
        updatedAt: chart.updated_at || chart.updatedAt || null
    });
}

function showCardPlaceholder(entry, message) {
    if (!entry?.messageEl) return;
    if (typeof message === 'string') {
        entry.messageEl.textContent = message;
    }
    entry.messageEl.classList.remove('hidden');
    if (entry.canvas) {
        entry.canvas.classList.add('hidden');
    }
}

function hideCardPlaceholder(entry) {
    if (!entry?.messageEl) return;
    entry.messageEl.classList.add('hidden');
    entry.messageEl.textContent = '';
    if (entry.canvas) {
        entry.canvas.classList.remove('hidden');
    }
}

function scheduleCanvasResize(entry) {
    if (!entry) return;
    const instance = chartInstances.get(entry.id);
    if (!instance || typeof instance.resize !== 'function') return;
    if (entry.resizeFrame) {
        return;
    }
    const resize = () => {
        entry.resizeFrame = null;
        try {
            instance.resize();
        } catch (error) {
            /* noop */
        }
    };
    if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
        entry.resizeFrame = window.requestAnimationFrame(resize);
    } else {
        entry.resizeFrame = setTimeout(resize, 32);
    }
}

function ensurePreviewResizeHandler() {
    if (state.previewResizeHandler || typeof window === 'undefined') return;
    state.previewResizeHandler = createThrottled(() => {
        state.chartCards.forEach((entry) => {
            if (entry.rendered) {
                scheduleCanvasResize(entry);
            }
        });
    }, 180);
    window.addEventListener('resize', state.previewResizeHandler, { passive: true });
}

function ensureLazyObserver() {
    if (state.lazyObserver) {
        return state.lazyObserver;
    }
    if (typeof window === 'undefined' || typeof IntersectionObserver === 'undefined') {
        return null;
    }
    state.lazyObserver = new IntersectionObserver((entries) => {
        entries.forEach((observerEntry) => {
            const chartId = Number.parseInt(observerEntry.target.dataset.chartId, 10);
            if (!Number.isFinite(chartId)) return;
            const cardEntry = state.chartCards.get(chartId);
            if (!cardEntry) return;
            cardEntry.isVisible = observerEntry.isIntersecting || observerEntry.intersectionRatio > 0;
            if (cardEntry.isVisible) {
                scheduleChartRender(chartId);
            }
        });
    }, { rootMargin: '200px 0px', threshold: 0.1 });
    return state.lazyObserver;
}

function createChartCardEntry(chart) {
    const card = document.createElement('div');
    const modalClass = ctx.themeClasses?.modal || '';
    card.className = `glass-panel ${modalClass} border border-white/5 rounded-3xl p-5 space-y-4`;
    card.dataset.chartId = chart.id;

    const header = document.createElement('div');
    header.className = 'flex items-start justify-between gap-3';

    const info = document.createElement('div');
    info.className = 'space-y-1';

    const title = document.createElement('h3');
    title.className = 'text-lg font-semibold';
    info.appendChild(title);

    const meta = document.createElement('p');
    meta.className = 'text-xs text-white/50 uppercase tracking-widest';
    info.appendChild(meta);

    const actions = document.createElement('div');
    actions.className = 'flex items-center gap-2';

    const viewBtn = document.createElement('button');
    viewBtn.className = 'p-2 rounded-full border border-transparent text-white/60 hover:text-emerald-300 hover:border-emerald-300 transition-colors';
    viewBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12s3.75-6.75 9.75-6.75S21.75 12 21.75 12s-3.75 6.75-9.75 6.75S2.25 12 2.25 12z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5z" />
        </svg>
    `;
    viewBtn.addEventListener('click', () => {
        const latest = state.charts.find((item) => item.id === chart.id);
        if (latest) {
            openViewModal(latest);
        }
    });

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'p-2 rounded-full border border-transparent text-white/60 hover:text-rose-400 hover:border-rose-400 transition-colors';
    deleteBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
    `;
    deleteBtn.addEventListener('click', () => {
        const latest = state.charts.find((item) => item.id === chart.id) || chart;
        openDeleteModal(latest);
    });

    actions.appendChild(viewBtn);
    actions.appendChild(deleteBtn);

    header.appendChild(info);
    header.appendChild(actions);

    const canvasWrapper = document.createElement('div');
    canvasWrapper.className = 'relative rounded-3xl border border-white/10 bg-white/5 h-[420px] overflow-hidden';

    const canvas = document.createElement('canvas');
    canvas.classList.add('hidden');
    canvasWrapper.appendChild(canvas);

    const message = document.createElement('div');
    message.className = 'absolute inset-0 flex items-center justify-center px-6 text-center text-sm text-white/60';
    message.textContent = 'Carregamento automático quando o cartão estiver visível.';
    canvasWrapper.appendChild(message);

    const details = document.createElement('p');
    details.className = 'text-xs text-white/50 uppercase tracking-widest';

    card.appendChild(header);
    card.appendChild(canvasWrapper);
    card.appendChild(details);

    const entry = {
        id: chart.id,
        card,
        titleEl: title,
        metaEl: meta,
        detailsEl: details,
        canvas,
        messageEl: message,
        viewBtn,
        deleteBtn,
        rendered: false,
        isVisible: false,
        needsRender: true,
        renderToken: 0,
        targetSignature: null,
        renderedSignature: null,
        resizeObserver: null,
        resizeFrame: null
    };

    if (typeof window !== 'undefined' && window.ResizeObserver) {
        try {
            entry.resizeObserver = new ResizeObserver(() => scheduleCanvasResize(entry));
            entry.resizeObserver.observe(canvasWrapper);
        } catch (error) {
            entry.resizeObserver = null;
        }
    }

    ensurePreviewResizeHandler();

    const observer = ensureLazyObserver();
    if (observer) {
        observer.observe(card);
    } else {
        entry.isVisible = true;
    }

    return entry;
}

function updateChartCard(entry, chart) {
    if (!entry) return;
    entry.card.dataset.chartId = chart.id;

    const chartLabel = getChartTypeLabel(chart.chart_type);
    const categoryLabel = slugToLabel(chart.categoria);
    const titleText = chart.nome || `${chartLabel} - ${categoryLabel}`;
    if (entry.titleEl && entry.titleEl.textContent !== titleText) {
        entry.titleEl.textContent = titleText;
    }

    if (entry.metaEl) {
        const metaText = `${categoryLabel} • ${chartLabel}`;
        if (entry.metaEl.textContent !== metaText) {
            entry.metaEl.textContent = metaText;
        }
    }

    const valueFields = Array.isArray(chart.value_fields) ? chart.value_fields : [];
    if (entry.detailsEl) {
        const detailsText = `Eixo: ${chart.dimension_field || '-'} • Valores: ${valueFields.length ? valueFields.join(', ') : '-'}`;
        if (entry.detailsEl.textContent !== detailsText) {
            entry.detailsEl.textContent = detailsText;
        }
    }

    if (entry.viewBtn) {
        entry.viewBtn.dataset.chartId = chart.id;
    }
    if (entry.deleteBtn) {
        entry.deleteBtn.dataset.chartId = chart.id;
    }
}

function ensureChartCard(chart) {
    let entry = state.chartCards.get(chart.id);
    if (!entry) {
        entry = createChartCardEntry(chart);
        state.chartCards.set(chart.id, entry);
    }

    updateChartCard(entry, chart);

    entry.targetSignature = `${state.renderVersion}:${computeChartSignature(chart)}`;
    if (entry.renderedSignature !== entry.targetSignature) {
        entry.needsRender = true;
        if (!entry.isVisible) {
            showCardPlaceholder(entry, 'Carregamento automático quando o cartão estiver visível.');
        }
    }

    return entry;
}

function removeChartCard(chartId) {
    const entry = state.chartCards.get(chartId);
    if (!entry) return;

    if (entry.resizeObserver) {
        try {
            entry.resizeObserver.disconnect();
        } catch (error) {
            /* noop */
        }
    }

    if (state.lazyObserver) {
        try {
            state.lazyObserver.unobserve(entry.card);
        } catch (error) {
            /* noop */
        }
    }

    const instance = chartInstances.get(chartId);
    if (instance && typeof instance.destroy === 'function') {
        instance.destroy();
    }
    chartInstances.delete(chartId);

    if (entry.card?.parentElement) {
        entry.card.parentElement.removeChild(entry.card);
    }

    state.chartCards.delete(chartId);
}

function scheduleChartRender(chartId) {
    const entry = state.chartCards.get(chartId);
    if (!entry) return;
    if (!entry.isVisible) {
        entry.needsRender = true;
        return;
    }
    if (!entry.needsRender && entry.rendered) {
        return;
    }
    if (state.pendingRenders.has(chartId)) {
        return;
    }
    state.pendingRenders.add(chartId);
    scheduleIdle(() => {
        state.pendingRenders.delete(chartId);
        const chart = state.charts.find((item) => item.id === chartId);
        if (!chart) {
            return;
        }
        const latestEntry = state.chartCards.get(chartId);
        if (!latestEntry) {
            return;
        }
        renderChartPreview(chart, latestEntry);
    }, 180);
}

function renderChartPreview(chart, entry) {
    if (!entry) return;

    entry.needsRender = false;
    entry.renderToken = (entry.renderToken || 0) + 1;
    const token = entry.renderToken;

    showCardPlaceholder(entry, 'Carregando visualização...');

    renderChartInstance(chart, entry.canvas, entry.messageEl, { disableAnimation: true, keepMessage: true })
        .then((instance) => {
            if (token !== entry.renderToken) {
                return;
            }
            entry.renderedSignature = entry.targetSignature;
            if (instance) {
                entry.rendered = true;
                hideCardPlaceholder(entry);
                scheduleCanvasResize(entry);
            } else {
                entry.rendered = false;
                entry.messageEl?.classList.remove('hidden');
            }
        })
        .catch(() => {
            if (token !== entry.renderToken) {
                return;
            }
            entry.rendered = false;
        });
}

function destroyViewChartInstance() {
    viewChartInstances.forEach((instance) => {
        if (instance && typeof instance.destroy === 'function') {
            instance.destroy();
        }
    });
    viewChartInstances.clear();
}

function updateViewModalNavigation() {
    if (!elements.nextViewModalBtn) return;
    const disabled = state.charts.length <= 1;
    elements.nextViewModalBtn.disabled = disabled;
    elements.nextViewModalBtn.classList.toggle('opacity-50', disabled);
    elements.nextViewModalBtn.classList.toggle('cursor-not-allowed', disabled);
}

function updateViewModalContent(chart) {
    if (!chart) return;
    const chartLabel = getChartTypeLabel(chart.chart_type);
    const categoryLabel = slugToLabel(chart.categoria);
    if (elements.viewChartTitle) {
        elements.viewChartTitle.textContent = chart.nome || `${chartLabel} - ${categoryLabel}`;
    }
    if (elements.viewChartMeta) {
        elements.viewChartMeta.textContent = `${categoryLabel} • ${chartLabel}`;
    }
}

function renderViewModalChart(chart) {
    if (!chart || !elements.viewChartCanvas) return;
    updateViewModalNavigation();
    state.viewRenderToken += 1;
    const token = state.viewRenderToken;
    destroyViewChartInstance();

    if (elements.viewChartMessage) {
        elements.viewChartMessage.classList.remove('hidden');
        elements.viewChartMessage.textContent = 'Carregando visualização...';
    }
    elements.viewChartCanvas.classList.add('hidden');

    renderChartInstance(chart, elements.viewChartCanvas, elements.viewChartMessage, {
        instanceStore: viewChartInstances,
        disableAnimation: false,
        keepMessage: true
    })
        .then((instance) => {
            if (token !== state.viewRenderToken) {
                return;
            }
            if (instance) {
                elements.viewChartCanvas.classList.remove('hidden');
                if (elements.viewChartMessage) {
                    elements.viewChartMessage.classList.add('hidden');
                    elements.viewChartMessage.textContent = '';
                }
            } else if (elements.viewChartMessage) {
                elements.viewChartMessage.classList.remove('hidden');
                if (!elements.viewChartMessage.textContent) {
                    elements.viewChartMessage.textContent = 'Não há dados suficientes para renderizar este gráfico.';
                }
            }
        })
        .catch((error) => {
            if (token !== state.viewRenderToken) {
                return;
            }
            if (elements.viewChartMessage) {
                elements.viewChartMessage.classList.remove('hidden');
                elements.viewChartMessage.textContent = error?.message || 'Falha ao carregar dados do gráfico.';
            }
            elements.viewChartCanvas.classList.add('hidden');
        });
}

function openViewModal(chart) {
    if (!chart || !elements.viewModal) return;
    state.currentViewId = chart.id;
    updateViewModalNavigation();
    updateViewModalContent(chart);
    renderViewModalChart(chart);
    elements.viewModal.classList.remove('hidden');
}

function closeViewModal() {
    if (!elements.viewModal) return;
    state.currentViewId = null;
    state.viewRenderToken += 1;
    destroyViewChartInstance();
    if (elements.viewChartMessage) {
        elements.viewChartMessage.classList.add('hidden');
        elements.viewChartMessage.textContent = '';
    }
    if (elements.viewChartCanvas) {
        elements.viewChartCanvas.classList.add('hidden');
    }
    elements.viewModal.classList.add('hidden');
}

function showNextViewChart() {
    if (state.charts.length <= 1) return;
    if (state.currentViewId === null) return;
    const currentIndex = state.charts.findIndex((item) => item.id === state.currentViewId);
    if (currentIndex === -1) {
        const fallback = state.charts[0];
        if (fallback) {
            state.currentViewId = fallback.id;
            updateViewModalContent(fallback);
            renderViewModalChart(fallback);
        } else {
            closeViewModal();
        }
        return;
    }
    const nextIndex = (currentIndex + 1) % state.charts.length;
    const nextChart = state.charts[nextIndex];
    if (!nextChart) {
        closeViewModal();
        return;
    }
    state.currentViewId = nextChart.id;
    updateViewModalContent(nextChart);
    renderViewModalChart(nextChart);
}

function prefetchDatasetsForCharts(charts, limit = 3) {
    const categories = [];
    charts.forEach((chart) => {
        const category = chart.categoria;
        if (!category) return;
        if (state.datasets.has(category) || state.datasetPromises.has(category) || state.prefetchedCategories.has(category)) {
            return;
        }
        if (!categories.includes(category)) {
            categories.push(category);
        }
    });
    categories.slice(0, limit).forEach((category, index) => {
        state.prefetchedCategories.add(category);
        scheduleIdle(() => {
            fetchDataset(category).catch(() => {});
        }, 200 + index * 150);
    });
}

function renderCharts() {
    if (!elements.chartsGrid) return;

    if (!state.charts.length) {
        if (elements.chartsEmptyState) {
            elements.chartsEmptyState.classList.remove('hidden');
        }
        if (elements.chartsSubtitle) {
            elements.chartsSubtitle.textContent = 'Crie seu primeiro gráfico para compartilhar insights das categorias da Análise JP.';
        }
        Array.from(state.chartCards.keys()).forEach((chartId) => removeChartCard(chartId));
        if (state.currentViewId !== null) {
            closeViewModal();
            updateViewModalNavigation();
        } else {
            updateViewModalNavigation();
        }
        return;
    }

    if (elements.chartsEmptyState) {
        elements.chartsEmptyState.classList.add('hidden');
    }
    if (elements.chartsSubtitle) {
        elements.chartsSubtitle.textContent = 'Explore as visualizações salvas para este workflow.';
    }

    const existingIds = new Set(state.chartCards.keys());
    let previousCard = null;

    state.charts.forEach((chart) => {
        const entry = ensureChartCard(chart);
        existingIds.delete(chart.id);

        const card = entry.card;
        if (card.parentElement !== elements.chartsGrid) {
            elements.chartsGrid.appendChild(card);
        }

        if (previousCard) {
            if (previousCard.nextSibling !== card) {
                elements.chartsGrid.insertBefore(card, previousCard.nextSibling);
            }
        } else if (elements.chartsGrid.firstChild !== card) {
            elements.chartsGrid.insertBefore(card, elements.chartsGrid.firstChild);
        }

        previousCard = card;

        if (entry.isVisible) {
            scheduleChartRender(chart.id);
        } else if (!entry.rendered) {
            showCardPlaceholder(entry, 'Carregamento automático quando o cartão estiver visível.');
        }
    });

    existingIds.forEach((chartId) => removeChartCard(chartId));

    if (state.currentViewId !== null) {
        const currentChart = state.charts.find((item) => item.id === state.currentViewId);
        if (!currentChart) {
            closeViewModal();
            updateViewModalNavigation();
        } else if (elements.viewModal && !elements.viewModal.classList.contains('hidden')) {
            updateViewModalContent(currentChart);
            renderViewModalChart(currentChart);
        } else {
            updateViewModalNavigation();
        }
    } else {
        updateViewModalNavigation();
    }

    prefetchDatasetsForCharts(state.charts.slice(0, 4));
}

async function refreshCharts() {
    const url = ctx.endpoints?.list;
    if (!url) return;
    try {
        const response = await fetch(url);
        const data = await response.json().catch(() => []);
        if (!response.ok) {
            throw new Error(data?.error || 'Não foi possível atualizar os gráficos.');
        }
        state.charts = Array.isArray(data) ? data : [];
        bumpRenderVersion();
        renderCharts();
        showToast('Galeria atualizada com sucesso.');
    } catch (error) {
        showToast(error.message || 'Falha ao atualizar gráficos.', 'error');
    }
}

function buildCreatePayload() {
    const categoria = elements.chartCategory?.value;
    const chartType = elements.chartType?.value;
    const dimension = elements.dimensionField?.value;
    const values = getSelectedValueFields();
    const nome = elements.chartTitle?.value?.trim();

    const payload = {
        categoria,
        chart_type: chartType,
        dimension_field: dimension,
        value_fields: values
    };
    if (nome) {
        payload.nome = nome;
    }
    return payload;
}

async function submitChart(event) {
    event.preventDefault();
    const payload = buildCreatePayload();

    if (!payload.categoria) {
        setFormFeedback('Selecione uma categoria com dados disponíveis.');
        return;
    }
    if (!payload.dimension_field) {
        setFormFeedback('Escolha um campo para o eixo principal.');
        return;
    }
    if (!payload.value_fields || !payload.value_fields.length) {
        setFormFeedback('Selecione ao menos um campo de valor.');
        return;
    }

    const url = ctx.endpoints?.create;
    if (!url) return;

    setFormFeedback('');
    setSubmitLoading(true);

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data?.error || 'Não foi possível criar o gráfico.');
        }
        if (data?.grafico) {
            state.charts.unshift(data.grafico);
            bumpRenderVersion();
            renderCharts();
            showToast('Gráfico criado com sucesso.');
            closeModal();
        }
    } catch (error) {
        setFormFeedback(error.message || 'Falha ao criar o gráfico.');
    } finally {
        setSubmitLoading(false);
    }
}

async function confirmDelete() {
    if (!state.pendingDelete) return;
    const url = buildDeleteUrl(state.pendingDelete);
    if (!url) return;

    setDeleteLoading(true);
    try {
        const response = await fetch(url, { method: 'DELETE' });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data?.error || 'Não foi possível remover o gráfico.');
        }
        state.charts = state.charts.filter((chart) => chart.id !== state.pendingDelete);
        bumpRenderVersion();
        chartInstances.get(state.pendingDelete)?.destroy();
        chartInstances.delete(state.pendingDelete);
        renderCharts();
        showToast('Gráfico removido com sucesso.');
        closeDeleteModal();
    } catch (error) {
        showToast(error.message || 'Falha ao remover o gráfico.', 'error');
        setDeleteLoading(false);
    }
}

function handleGlobalClick(event) {
    if (event.target === elements.chartModalOverlay) {
        closeModal();
    }
    if (event.target === elements.deleteModalOverlay) {
        closeDeleteModal();
    }
    if (event.target === elements.viewModalOverlay) {
        closeViewModal();
    }
}

function initEvents() {
    if (elements.openModalBtn) {
        elements.openModalBtn.addEventListener('click', openModal);
    }
    if (elements.emptyStateCreateBtn) {
        elements.emptyStateCreateBtn.addEventListener('click', openModal);
    }
    if (elements.closeModalBtn) {
        elements.closeModalBtn.addEventListener('click', closeModal);
    }
    if (elements.cancelModalBtn) {
        elements.cancelModalBtn.addEventListener('click', closeModal);
    }
    if (elements.chartCategory) {
        elements.chartCategory.addEventListener('change', (event) => {
            const value = event.target.value;
            updateCategoryHint(value);
            loadFieldsForCategory(value);
        });
    }
    if (elements.toggleSelectAllValues) {
        elements.toggleSelectAllValues.addEventListener('click', toggleSelectAllValues);
    }
    if (elements.chartForm) {
        elements.chartForm.addEventListener('submit', submitChart);
    }
    if (elements.refreshBtn) {
        elements.refreshBtn.addEventListener('click', refreshCharts);
    }
    if (elements.chartModalOverlay) {
        elements.chartModalOverlay.addEventListener('click', closeModal);
    }
    if (elements.deleteModalOverlay) {
        elements.deleteModalOverlay.addEventListener('click', closeDeleteModal);
    }
    if (elements.cancelDeleteBtn) {
        elements.cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    }
    if (elements.closeDeleteModalBtn) {
        elements.closeDeleteModalBtn.addEventListener('click', closeDeleteModal);
    }
    if (elements.confirmDeleteBtn) {
        elements.confirmDeleteBtn.addEventListener('click', confirmDelete);
    }
    if (elements.closeViewModalBtn) {
        elements.closeViewModalBtn.addEventListener('click', closeViewModal);
    }
    if (elements.viewModalOverlay) {
        elements.viewModalOverlay.addEventListener('click', closeViewModal);
    }
    if (elements.nextViewModalBtn) {
        elements.nextViewModalBtn.addEventListener('click', showNextViewChart);
    }
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (!elements.chartModal?.classList.contains('hidden')) {
                closeModal();
            }
            if (!elements.deleteModal?.classList.contains('hidden')) {
                closeDeleteModal();
            }
            if (!elements.viewModal?.classList.contains('hidden')) {
                closeViewModal();
            }
        }
    });
    document.addEventListener('click', handleGlobalClick);
}

function init() {
    renderCharts();
    initEvents();
}

init();
