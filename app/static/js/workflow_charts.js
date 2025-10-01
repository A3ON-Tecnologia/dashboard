const ctx = window.__CHARTS_DATA__ || {};

const METRIC_OPTIONS = [
    { value: 'valor_periodo_1', label: 'Valor periodo 1' },
    { value: 'valor_periodo_2', label: 'Valor periodo 2' },
    { value: 'diferenca_absoluta', label: 'Diferenca absoluta' },
    { value: 'diferenca_percentual', label: 'Diferenca percentual' }
];

const state = {
    charts: Array.isArray(ctx.charts) ? [...ctx.charts] : [],
    pendingDelete: null,
    selectedIndicators: [],
    selectedMetrics: [METRIC_OPTIONS[0].value],
    activeDropdown: null,
    resizeObservers: new Map(),
    currentViewId: null,
    viewRenderToken: 0,
    viewResizeHandler: null
};

const elements = {
    indicatorToggle: document.getElementById('indicatorToggle'),
    indicatorDropdown: document.getElementById('indicatorDropdown'),
    indicatorOptions: document.getElementById('indicatorOptions'),
    indicatorLabel: document.getElementById('indicatorSelectionLabel'),
    metricToggle: document.getElementById('metricToggle'),
    metricDropdown: document.getElementById('metricDropdown'),
    metricOptions: document.getElementById('metricOptions'),
    metricLabel: document.getElementById('metricSelectionLabel'),
    colorContainer: document.getElementById('colorPickerContainer'),
    openModalBtn: document.getElementById('openCreateChartBtn'),
    refreshBtn: document.getElementById('refreshChartsBtn'),
    chartModal: document.getElementById('chartModal'),
    chartForm: document.getElementById('chartForm'),
    submitBtn: document.getElementById('submitChartBtn'),
    submitSpinner: document.getElementById('chartSubmitSpinner'),
    formFeedback: document.getElementById('chartFormFeedback'),
    chartsGrid: document.getElementById('chartsGrid'),
    emptyState: document.getElementById('chartsEmptyState'),
    chartsSubtitle: document.getElementById('chartsSubtitle'),
    deleteModal: document.getElementById('chartDeleteModal'),
    deleteName: document.getElementById('deleteChartName'),
    confirmDeleteBtn: document.getElementById('confirmDeleteChartBtn'),
    cancelDeleteBtn: document.getElementById('cancelDeleteChartBtn'),
    toastContainer: document.getElementById('toastContainer'),
    viewModal: document.getElementById('viewChartModal'),
    viewModalOverlay: document.getElementById('viewChartModalOverlay'),
    closeViewModalBtn: document.getElementById('closeViewChartBtn'),
    nextViewModalBtn: document.getElementById('nextViewChartBtn'),
    viewChartTitle: document.getElementById('viewChartTitle'),
    viewChartMeta: document.getElementById('viewChartMeta'),
    viewChartCanvas: document.getElementById('viewChartCanvas'),
    viewChartMessage: document.getElementById('viewChartMessage')
};

const indicatorMap = new Map(
    ctx.processedData && Array.isArray(ctx.processedData?.indicadores)
        ? ctx.processedData.indicadores.map((item) => [item.indicador, item])
        : []
);

const chartPalette = Array.isArray(ctx.themePalette) && ctx.themePalette.length
    ? ctx.themePalette
    : ['#3B82F6', '#22D3EE', '#A855F7', '#F97316', '#14B8A6', '#FACC15'];

const seriesFriendlyNames = Object.fromEntries(METRIC_OPTIONS.map((option) => [option.value, option.label]));

function logout() {
    fetch('/logout')
        .then((response) => response.json())
        .then((data) => {
            if (data.message) {
                window.location.href = '/';
            }
        });
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    const baseClass = 'glass-panel border border-white/10 rounded-2xl px-4 py-3 flex items-center gap-3 text-sm shadow-lg animate__animated animate__fadeInUp';
    const themeClass = type === 'error'
        ? (ctx.themeClasses?.toastError || 'bg-rose-600 text-white')
        : (ctx.themeClasses?.toastSuccess || 'bg-emerald-600 text-white');
    toast.className = `${baseClass} ${themeClass}`;
    toast.textContent = message;
    elements.toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-2');
        setTimeout(() => toast.remove(), 200);
    }, 3200);
}

function metricLabel(metric) {
    return seriesFriendlyNames[metric] || metric;
}

function chartTypeLabel(type) {
    if (!type) return '';
    return String(type)
        .split('_')
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ');
}

function closeAllDropdowns() {
    elements.indicatorDropdown?.classList.add('hidden');
    elements.metricDropdown?.classList.add('hidden');
    state.activeDropdown = null;
}

function toggleDropdown(target) {
    const dropdown = target === 'indicator' ? elements.indicatorDropdown : elements.metricDropdown;
    if (!dropdown) return;

    if (state.activeDropdown === target) {
        closeAllDropdowns();
        return;
    }

    closeAllDropdowns();
    dropdown.classList.remove('hidden');
    state.activeDropdown = target;
}

function updateIndicatorLabel() {
    if (!elements.indicatorLabel) return;
    const items = state.selectedIndicators;
    if (!items.length) {
        elements.indicatorLabel.textContent = 'Nenhum indicador';
    } else if (items.length === 1) {
        elements.indicatorLabel.textContent = items[0];
    } else if (items.length === 2) {
        elements.indicatorLabel.textContent = `${items[0]}, ${items[1]}`;
    } else {
        elements.indicatorLabel.textContent = `${items.length} indicadores`;
    }
}

function updateMetricLabel() {
    if (!elements.metricLabel) return;
    const items = state.selectedMetrics;
    if (!items.length) {
        elements.metricLabel.textContent = 'Nenhuma metrica';
    } else if (items.length === 1) {
        elements.metricLabel.textContent = metricLabel(items[0]);
    } else if (items.length === 2) {
        elements.metricLabel.textContent = `${metricLabel(items[0])}, ${metricLabel(items[1])}`;
    } else {
        elements.metricLabel.textContent = `${items.length} metricas`;
    }
}

function populateIndicatorOptions(force = false) {
    if (!elements.indicatorOptions) return;
    const keys = Array.from(indicatorMap.keys());

    if (!state.selectedIndicators.length || force) {
        state.selectedIndicators = keys.slice(0, Math.min(3, keys.length));
    } else {
        state.selectedIndicators = state.selectedIndicators.filter((value) => indicatorMap.has(value));
        if (!state.selectedIndicators.length && keys.length) {
            state.selectedIndicators = [keys[0]];
        }
    }

    elements.indicatorOptions.innerHTML = '';

    if (!keys.length) {
        const emptyEl = document.createElement('p');
        emptyEl.className = 'text-xs text-white/50';
        emptyEl.textContent = 'Nenhum indicador disponivel.';
        elements.indicatorOptions.appendChild(emptyEl);
        if (elements.openModalBtn) {
            elements.openModalBtn.disabled = true;
            elements.openModalBtn.classList.add('opacity-60', 'cursor-not-allowed');
        }
        updateIndicatorLabel();
        return;
    }

    keys.forEach((key) => {
        const option = document.createElement('label');
        option.className = 'flex items-center gap-3 rounded-xl px-3 py-2 hover:bg-white/10 transition-colors cursor-pointer';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = key;
        checkbox.className = 'h-4 w-4 rounded border-white/20 bg-transparent';
        checkbox.checked = state.selectedIndicators.includes(key);

        checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
                if (!state.selectedIndicators.includes(key)) {
                    state.selectedIndicators.push(key);
                }
            } else {
                if (state.selectedIndicators.length === 1) {
                    checkbox.checked = true;
                    return;
                }
                state.selectedIndicators = state.selectedIndicators.filter((value) => value !== key);
            }
            updateIndicatorLabel();
            updateColorPickers();
        });

        const name = document.createElement('span');
        name.className = 'text-sm text-white/80 truncate';
        name.textContent = key;

        option.appendChild(checkbox);
        option.appendChild(name);
        elements.indicatorOptions.appendChild(option);
    });

    if (elements.openModalBtn) {
        elements.openModalBtn.disabled = false;
        elements.openModalBtn.classList.remove('opacity-60', 'cursor-not-allowed');
    }

    updateIndicatorLabel();
}

function populateMetricOptions(force = false) {
    if (!elements.metricOptions) return;

    const values = METRIC_OPTIONS.map((option) => option.value);
    if (!state.selectedMetrics.length || force) {
        state.selectedMetrics = [values[0]];
    } else {
        state.selectedMetrics = state.selectedMetrics.filter((value) => values.includes(value));
        if (!state.selectedMetrics.length) {
            state.selectedMetrics = [values[0]];
        }
    }

    elements.metricOptions.innerHTML = '';

    METRIC_OPTIONS.forEach((option) => {
        const row = document.createElement('label');
        row.className = 'flex items-center gap-3 rounded-xl px-3 py-2 hover:bg-white/10 transition-colors cursor-pointer';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = option.value;
        checkbox.className = 'h-4 w-4 rounded border-white/20 bg-transparent';
        checkbox.checked = state.selectedMetrics.includes(option.value);

        checkbox.addEventListener('change', () => {
            if (checkbox.checked) {
                if (!state.selectedMetrics.includes(option.value)) {
                    state.selectedMetrics.push(option.value);
                }
            } else {
                if (state.selectedMetrics.length === 1) {
                    checkbox.checked = true;
                    return;
                }
                state.selectedMetrics = state.selectedMetrics.filter((value) => value !== option.value);
            }
            updateMetricLabel();
            updateColorPickers();
        });

        const label = document.createElement('span');
        label.className = 'text-sm text-white/80 truncate';
        label.textContent = option.label;

        row.appendChild(checkbox);
        row.appendChild(label);
        elements.metricOptions.appendChild(row);
    });

    updateMetricLabel();
}

function updateColorPickers() {
    if (!elements.colorContainer) return;

    const previous = new Map(
        Array.from(elements.colorContainer.querySelectorAll('input[type="color"]')).map((input) => [input.dataset.key, input.value])
    );

    elements.colorContainer.innerHTML = '';

    if (!state.selectedIndicators.length) {
        const info = document.createElement('p');
        info.className = 'text-xs text-white/40';
        info.textContent = 'Selecione pelo menos um indicador.';
        elements.colorContainer.appendChild(info);
        return;
    }

    const useMetricPalette = state.selectedMetrics.length > 1;
    const items = useMetricPalette ? state.selectedMetrics : state.selectedIndicators;

    items.forEach((item, index) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'flex items-center justify-between gap-3 rounded-2xl px-4 py-3 bg-white/5 border border-white/10';

        const label = document.createElement('span');
        label.className = 'text-sm text-white/70 truncate';
        label.textContent = useMetricPalette ? metricLabel(item) : item;

        const input = document.createElement('input');
        input.type = 'color';
        input.dataset.key = item;
        input.value = previous.get(item) || (chartPalette[index % chartPalette.length] || '#3B82F6');
        input.className = 'w-12 h-8 rounded-lg border border-white/20 bg-transparent cursor-pointer';

        wrapper.appendChild(label);
        wrapper.appendChild(input);
        elements.colorContainer.appendChild(wrapper);
    });
}
function openChartModal() {
    if (elements.openModalBtn?.disabled) {
        showToast('Importe um arquivo para liberar os graficos.', 'error');
        return;
    }
    resetChartForm();
    closeAllDropdowns();
    elements.chartModal?.classList.remove('hidden');
    elements.chartModal?.classList.add('flex');
}

function closeChartModal() {
    elements.chartModal?.classList.add('hidden');
    elements.chartModal?.classList.remove('flex');
}

function resetChartForm() {
    elements.chartForm?.reset();
    elements.formFeedback.textContent = '';
    elements.submitSpinner.classList.add('hidden');
    elements.submitBtn.disabled = false;
    elements.submitBtn.classList.remove('opacity-70', 'cursor-not-allowed');

    populateMetricOptions(true);
    populateIndicatorOptions(true);
    updateColorPickers();
}

function metricValue(indicator, metric) {
    if (!indicator) return null;
    const value = indicator[metric];
    if (value === null || value === undefined) return null;
    if (typeof value === 'number') return value;
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
}

function buildPayloadFromForm() {
    const payload = {
        nome: document.getElementById('chartTitle').value.trim(),
        chart_type: document.getElementById('chartType').value,
        indicators: [...state.selectedIndicators],
        metrics: [...state.selectedMetrics]
    };

    const useMetricPalette = state.selectedMetrics.length > 1;
    const keys = useMetricPalette ? state.selectedMetrics : state.selectedIndicators;
    payload.colors = keys.map((key, index) => {
        const input = elements.colorContainer.querySelector(`input[data-key="${key}"]`);
        if (input) {
            return input.value.toUpperCase();
        }
        return (chartPalette[index % chartPalette.length] || '#3B82F6').toUpperCase();
    });

    return payload;
}

function handleChartSubmit(event) {
    event.preventDefault();
    const payload = buildPayloadFromForm();

    if (!payload.indicators.length) {
        elements.formFeedback.textContent = 'Selecione pelo menos um indicador.';
        elements.formFeedback.className = 'text-sm text-center text-rose-300';
        return;
    }

    if (!payload.metrics.length) {
        elements.formFeedback.textContent = 'Selecione pelo menos uma metrica.';
        elements.formFeedback.className = 'text-sm text-center text-rose-300';
        return;
    }

    elements.submitBtn.disabled = true;
    elements.submitBtn.classList.add('opacity-70', 'cursor-not-allowed');
    elements.submitSpinner.classList.remove('hidden');
    elements.formFeedback.textContent = '';

    fetch(ctx.endpoints.create, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok) {
                throw new Error(data.error || 'Erro ao criar grafico.');
            }
            state.charts.unshift(data.grafico);
            renderCharts();
            closeChartModal();
            showToast(data.message || 'Grafico criado com sucesso.', 'success');
        })
        .catch((error) => {
            elements.formFeedback.textContent = error.message;
            elements.formFeedback.className = 'text-sm text-center text-rose-300';
            showToast(error.message, 'error');
        })
        .finally(() => {
            elements.submitBtn.disabled = false;
            elements.submitBtn.classList.remove('opacity-70', 'cursor-not-allowed');
            elements.submitSpinner.classList.add('hidden');
        });
}

function getChartMetrics(chart) {
    const metrics = Array.isArray(chart.options?.metrics) && chart.options.metrics.length
        ? chart.options.metrics
        : (chart.metric ? [chart.metric] : []);
    return metrics.filter((metric) => METRIC_OPTIONS.some((option) => option.value === metric));
}

function getChartContainerSizing(type) {
    const normalized = (type || '').toLowerCase();
    switch (normalized) {
        case 'pie':
        case 'doughnut':
            return { minHeight: '440px', maxHeight: '560px' };
        case 'gauge':
            return { minHeight: '420px', maxHeight: '540px' };
        case 'table':
            return { minHeight: '380px', maxHeight: '520px' };
        case 'radar':
            return { minHeight: '460px', maxHeight: '620px' };
        case 'heatmap':
            return { minHeight: '440px', maxHeight: '600px' };
        default:
            return { minHeight: '460px', maxHeight: '640px' };
    }
}

function buildFigure(chart) {
    const metrics = getChartMetrics(chart);
    const metricsList = metrics.length ? metrics : (chart.metric ? [chart.metric] : []);

    const selectedIndicators = chart.indicators
        .map((name) => ({ name, data: indicatorMap.get(name) }))
        .filter((item) => item.data);

    if (!selectedIndicators.length || !metricsList.length) {
        return null;
    }

    const chartType = chart.chart_type;
    const supportsMultiMetrics = ['bar', 'line', 'area', 'scatter'];
    const useMetricSeries = supportsMultiMetrics.includes(chartType) && metricsList.length > 1;
    const colourPalette = Array.isArray(chart.colors) && chart.colors.length ? chart.colors : chartPalette;

    const names = selectedIndicators.map((item) => item.name);

    let data = [];
    let layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: ctx.themeName === 'light' ? '#0f172a' : '#f8fafc', family: 'Space Grotesk, sans-serif' },
        margin: { t: 40, l: 40, r: 20, b: 40 },
        hoverlabel: { font: { family: 'Space Grotesk, sans-serif' } }
    };

    if (useMetricSeries) {
        metricsList.forEach((metric, index) => {
            const values = selectedIndicators.map((item) => metricValue(item.data, metric));
            const color = (colourPalette[index] || chartPalette[index % chartPalette.length] || '#3B82F6');
            const friendly = metricLabel(metric);

            if (chartType === 'bar') {
                data.push({
                    type: 'bar',
                    name: friendly,
                    x: names,
                    y: values,
                    marker: { color },
                    hovertemplate: `%{x}<br>${friendly}: %{y}<extra></extra>`
                });
            } else if (chartType === 'line') {
                data.push({
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: friendly,
                    x: names,
                    y: values,
                    line: { color, width: 3 },
                    marker: { color, size: 9 },
                    hovertemplate: `%{x}<br>${friendly}: %{y}<extra></extra>`
                });
            } else if (chartType === 'area') {
                data.push({
                    type: 'scatter',
                    mode: 'lines',
                    fill: 'tozeroy',
                    name: friendly,
                    x: names,
                    y: values,
                    line: { color, width: 2 },
                    fillcolor: `${color}33`,
                    hovertemplate: `%{x}<br>${friendly}: %{y}<extra></extra>`
                });
            } else if (chartType === 'scatter') {
                data.push({
                    type: 'scatter',
                    mode: 'markers',
                    name: friendly,
                    x: names,
                    y: values,
                    marker: { color, size: 12 },
                    hovertemplate: `%{x}<br>${friendly}: %{y}<extra></extra>`
                });
            }
        });

        if (chartType === 'bar') {
            layout.barmode = 'group';
        }
        layout.xaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)' };
        layout.yaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)', zerolinecolor: 'rgba(255, 255, 255, 0.08)' };
    } else {
        const metric = metricsList[0];
        const friendly = metricLabel(metric);
        const values = selectedIndicators.map((item) => metricValue(item.data, metric));

        switch (chartType) {
            case 'bar':
                data = [{
                    type: 'bar',
                    x: names,
                    y: values,
                    marker: { color: chart.indicators.map((_, index) => colourPalette[index % colourPalette.length]) },
                    hovertemplate: `%{x}<br>${friendly}: %{y}<extra></extra>`
                }];
                layout.xaxis = { tickangle: -15, gridcolor: 'rgba(255, 255, 255, 0.08)' };
                layout.yaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)', zerolinecolor: 'rgba(255, 255, 255, 0.08)' };
                break;
            case 'line':
                data = [{
                    type: 'scatter',
                    mode: 'lines+markers',
                    x: names,
                    y: values,
                    line: { color: colourPalette[0] || '#3B82F6', width: 3 },
                    marker: { color: chart.indicators.map((_, index) => colourPalette[index % colourPalette.length]), size: 9 },
                    hovertemplate: `%{x}<br>${friendly}: %{y}<extra></extra>`
                }];
                layout.xaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)' };
                layout.yaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)', zerolinecolor: 'rgba(255, 255, 255, 0.08)' };
                break;
            case 'area':
                data = [{
                    type: 'scatter',
                    mode: 'lines',
                    fill: 'tozeroy',
                    x: names,
                    y: values,
                    line: { color: colourPalette[0] || '#3B82F6', width: 2 },
                    fillcolor: `${(colourPalette[0] || '#3B82F6')}33`,
                    hovertemplate: `%{x}<br>${friendly}: %{y}<extra></extra>`
                }];
                layout.xaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)' };
                layout.yaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)', zerolinecolor: 'rgba(255, 255, 255, 0.08)' };
                break;
            case 'pie':
                data = [{
                    type: 'pie',
                    labels: names,
                    values,
                    marker: { colors: chart.indicators.map((_, index) => colourPalette[index % colourPalette.length]) },
                    hole: 0,
                    hovertemplate: `%{label}<br>${friendly}: %{value}<extra></extra>`
                }];
                layout.margin = { t: 20, b: 20, l: 20, r: 20 };
                break;
            case 'doughnut':
                data = [{
                    type: 'pie',
                    labels: names,
                    values,
                    marker: { colors: chart.indicators.map((_, index) => colourPalette[index % colourPalette.length]) },
                    hole: 0.45,
                    hovertemplate: `%{label}<br>${friendly}: %{value}<extra></extra>`
                }];
                layout.margin = { t: 20, b: 20, l: 20, r: 20 };
                break;
            case 'radar':
                data = [{
                    type: 'scatterpolar',
                    r: values,
                    theta: names,
                    fill: 'toself',
                    line: { color: colourPalette[0] || '#3B82F6' },
                    marker: { color: colourPalette[0] || '#3B82F6' },
                    hovertemplate: `%{theta}<br>${friendly}: %{r}<extra></extra>`
                }];
                layout.polar = {
                    bgcolor: 'rgba(0,0,0,0)',
                    radialaxis: { gridcolor: 'rgba(255, 255, 255, 0.08)', color: '#94a3b8' },
                    angularaxis: { gridcolor: 'rgba(255, 255, 255, 0.08)', color: '#94a3b8' }
                };
                break;
            case 'scatter':
                data = [{
                    type: 'scatter',
                    mode: 'markers',
                    x: names,
                    y: values,
                    marker: { color: chart.indicators.map((_, index) => colourPalette[index % colourPalette.length]), size: 12 },
                    hovertemplate: `%{x}<br>${friendly}: %{y}<extra></extra>`
                }];
                layout.xaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)' };
                layout.yaxis = { gridcolor: 'rgba(255, 255, 255, 0.08)', zerolinecolor: 'rgba(255, 255, 255, 0.08)' };
                break;
            case 'heatmap':
                data = [{
                    type: 'heatmap',
                    z: [values],
                    x: names,
                    y: [friendly],
                    colorscale: 'Viridis',
                    showscale: true,
                    hovertemplate: `%{x}<br>${friendly}: %{z}<extra></extra>`
                }];
                layout.xaxis = { side: 'top' };
                layout.yaxis = { automargin: true };
                break;
            case 'gauge':
                data = [{
                    type: 'indicator',
                    mode: 'gauge+number',
                    value: values[0] ?? 0,
                    title: { text: names[0] || 'Indicador', font: { color: '#f8fafc' } },
                    gauge: {
                        axis: {
                            range: metric === 'diferenca_percentual' ? [-100, 100] : [0, Math.max(Math.abs(values[0] ?? 0) * 1.2, 1)],
                            tickcolor: '#94a3b8'
                        },
                        bar: { color: colourPalette[0] || '#3B82F6' },
                        bgcolor: 'transparent'
                    }
                }];
                layout.margin = { t: 40, b: 40, l: 40, r: 40 };
                break;
            case 'table':
                data = [{
                    type: 'table',
                    header: {
                        values: [['Indicador'], [friendly]],
                        align: 'center',
                        fill: { color: colourPalette[0] || '#1f2937' },
                        font: { color: '#ffffff', size: 12, family: 'Space Grotesk, sans-serif' }
                    },
                    cells: {
                        values: [names, values.map((value) => value ?? '-')],
                        align: 'center',
                        fill: { color: 'rgba(255,255,255,0.04)' },
                        font: { color: '#e2e8f0', size: 12, family: 'Space Grotesk, sans-serif' }
                    }
                }];
                layout.margin = { t: 20, b: 20, l: 10, r: 10 };
                break;
            default:
                return null;
        }
    }

    layout.title = {
        text: chart.nome || `${chart.chart_type} - ${metricsList.map(metricLabel).join(' / ')}`,
        font: { family: 'Space Grotesk, sans-serif', size: 18 }
    };

    return { data, layout };
}

function isViewModalOpen() {
    return Boolean(elements.viewModal && !elements.viewModal.classList.contains('hidden'));
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
    const metricsList = getChartMetrics(chart);
    const metricSummary = metricsList.length ? metricsList.map(metricLabel).join(', ') : metricLabel(chart.metric || '');
    if (elements.viewChartTitle) {
        const chartLabel = chartTypeLabel(chart.chart_type || chart.chartType);
        elements.viewChartTitle.textContent = chart.nome || chartLabel || 'Visualização';
    }
    if (elements.viewChartMeta) {
        const indicators = Array.isArray(chart.indicators) && chart.indicators.length ? chart.indicators.join(', ') : 'n/d';
        const chartLabel = chartTypeLabel(chart.chart_type || chart.chartType);
        const parts = [];
        if (chartLabel) {
            parts.push(chartLabel);
        }
        parts.push(`Métricas: ${metricSummary || 'n/d'}`);
        parts.push(`Indicadores: ${indicators}`);
        elements.viewChartMeta.textContent = parts.join(' • ');
    }
}

function ensureViewResizeHandler() {
    if (state.viewResizeHandler || typeof window === 'undefined') return;
    state.viewResizeHandler = () => {
        if (!isViewModalOpen() || !elements.viewChartCanvas) return;
        try {
            Plotly.Plots.resize(elements.viewChartCanvas);
        } catch (error) {
            /* noop */
        }
    };
    window.addEventListener('resize', state.viewResizeHandler, { passive: true });
}

function removeViewResizeHandler() {
    if (!state.viewResizeHandler || typeof window === 'undefined') return;
    window.removeEventListener('resize', state.viewResizeHandler);
    state.viewResizeHandler = null;
}

function destroyViewChartInstance() {
    if (elements.viewChartCanvas) {
        try {
            Plotly.purge(elements.viewChartCanvas);
        } catch (error) {
            /* noop */
        }
        elements.viewChartCanvas.innerHTML = '';
        elements.viewChartCanvas.classList.add('hidden');
    }
}

function renderViewModalChart(chart) {
    if (!chart || !elements.viewChartCanvas) return;
    const figure = buildFigure(chart);
    state.viewRenderToken += 1;
    const token = state.viewRenderToken;

    destroyViewChartInstance();

    if (!figure) {
        if (elements.viewChartMessage) {
            elements.viewChartMessage.textContent = 'Não há dados suficientes para exibir este gráfico.';
            elements.viewChartMessage.classList.remove('hidden');
        }
        removeViewResizeHandler();
        return;
    }

    if (elements.viewChartMessage) {
        elements.viewChartMessage.classList.add('hidden');
        elements.viewChartMessage.textContent = '';
    }

    elements.viewChartCanvas.classList.remove('hidden');
    elements.viewChartCanvas.style.width = '100%';
    elements.viewChartCanvas.style.height = '100%';

    const layout = { ...figure.layout };
    const config = {
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['lasso2d', 'autoScale2d']
    };

    Plotly.newPlot(elements.viewChartCanvas, figure.data, layout, config)
        .then(() => {
            if (token !== state.viewRenderToken) {
                return;
            }
            try {
                Plotly.Plots.resize(elements.viewChartCanvas);
            } catch (error) {
                /* noop */
            }
            ensureViewResizeHandler();
        })
        .catch((error) => {
            if (token !== state.viewRenderToken) {
                return;
            }
            destroyViewChartInstance();
            removeViewResizeHandler();
            if (elements.viewChartMessage) {
                elements.viewChartMessage.textContent = error.message || 'Falha ao carregar o gráfico.';
                elements.viewChartMessage.classList.remove('hidden');
            }
        });
}

function openViewModal(chart) {
    if (!chart || !elements.viewModal) return;
    state.currentViewId = chart.id;
    updateViewModalNavigation();
    updateViewModalContent(chart);
    renderViewModalChart(chart);
    elements.viewModal.classList.remove('hidden');
    elements.viewModal.classList.add('flex');
}

function closeViewModal() {
    if (!elements.viewModal) return;
    state.currentViewId = null;
    state.viewRenderToken += 1;
    destroyViewChartInstance();
    removeViewResizeHandler();
    if (elements.viewChartMessage) {
        elements.viewChartMessage.classList.add('hidden');
        elements.viewChartMessage.textContent = '';
    }
    elements.viewModal.classList.add('hidden');
    elements.viewModal.classList.remove('flex');
}

function showNextViewChart() {
    if (state.charts.length <= 1) return;
    if (state.currentViewId === null) return;

    const currentIndex = state.charts.findIndex((item) => item.id === state.currentViewId);
    if (currentIndex === -1) {
        const fallback = state.charts[0];
        if (!fallback) {
            closeViewModal();
            return;
        }
        state.currentViewId = fallback.id;
        updateViewModalContent(fallback);
        renderViewModalChart(fallback);
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
function renderCharts() {
    if (!elements.chartsGrid) return;
    elements.chartsGrid.innerHTML = '';

    if (state.resizeObservers instanceof Map) {
        state.resizeObservers.forEach((observer) => {
            try { observer.disconnect(); } catch (error) { /* noop */ }
        });
        state.resizeObservers.clear();
    }

    if (!state.charts.length) {
        elements.emptyState?.classList.remove('hidden');
        if (elements.chartsSubtitle) {
            elements.chartsSubtitle.textContent = 'Crie seu primeiro grafico para transformar os indicadores em insights visuais.';
        }
        if (isViewModalOpen() || state.currentViewId !== null) {
            closeViewModal();
        } else {
            state.currentViewId = null;
        }
        updateViewModalNavigation();
        return;
    }

    elements.emptyState?.classList.add('hidden');
    if (elements.chartsSubtitle) {
        elements.chartsSubtitle.textContent = 'Explore visualizacoes criadas para este workflow.';
    }

    state.charts.forEach((chart) => {
        const card = document.createElement('article');
        card.className = `glass-panel ${ctx.themeClasses?.modalSurface || ''} border border-white/10 rounded-3xl p-5 space-y-5 shadow-lg shadow-blue-500/10`;
        card.dataset.chartId = chart.id;

        const header = document.createElement('div');
        header.className = 'flex items-start justify-between gap-3';

        const metricsList = getChartMetrics(chart);
        const metricSummary = metricsList.length ? metricsList.map(metricLabel).join(', ') : metricLabel(chart.metric || '');
        const indicatorSummary = Array.isArray(chart.indicators) && chart.indicators.length
            ? chart.indicators.join(', ')
            : 'n/d';
        const chartLabel = chartTypeLabel(chart.chart_type || chart.chartType);

        const info = document.createElement('div');
        info.className = 'space-y-1';

        const title = document.createElement('h3');
        title.className = 'text-lg font-semibold';
        title.textContent = chart.nome || chartLabel || chart.chart_type || 'Grafico';
        info.appendChild(title);

        if (chartLabel) {
            const typeLine = document.createElement('p');
            typeLine.className = 'text-xs text-white/50 uppercase tracking-widest';
            typeLine.textContent = `Tipo: ${chartLabel}`;
            info.appendChild(typeLine);
        }

        const metricsLine = document.createElement('p');
        metricsLine.className = 'text-xs text-white/60';
        metricsLine.textContent = `Metricas: ${metricSummary || 'n/d'}`;
        info.appendChild(metricsLine);

        const indicatorsLine = document.createElement('p');
        indicatorsLine.className = 'text-xs text-white/60';
        indicatorsLine.textContent = `Indicadores: ${indicatorSummary}`;
        info.appendChild(indicatorsLine);

        const actions = document.createElement('div');
        actions.className = 'flex items-center gap-2';

        const viewBtn = document.createElement('button');
        viewBtn.className = 'p-2 rounded-full border border-transparent text-white/60 hover:text-blue-300 hover:border-blue-300 transition-colors';
        viewBtn.dataset.viewChart = chart.id;
        viewBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12s3.75-6.75 9.75-6.75S21.75 12 21.75 12s-3.75 6.75-9.75 6.75S2.25 12 2.25 12z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5z" />
            </svg>
        `;
        actions.appendChild(viewBtn);

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'p-2 rounded-full border border-transparent text-white/60 hover:text-rose-400 hover:border-rose-400 transition-colors';
        deleteBtn.dataset.deleteChart = chart.id;
        deleteBtn.dataset.chartName = chart.nome || chartLabel || chart.chart_type || 'este grafico';
        deleteBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
        `;
        actions.appendChild(deleteBtn);

        header.appendChild(info);
        header.appendChild(actions);

        const plotId = `chart-plot-${chart.id}`;
        const sizing = getChartContainerSizing(chart.chart_type || chart.chartType);

        const plotWrapper = document.createElement('div');
        plotWrapper.className = 'chart-plot-wrapper';
        plotWrapper.style.minHeight = sizing?.minHeight || '460px';
        if (sizing?.maxHeight) {
            plotWrapper.style.maxHeight = sizing.maxHeight;
        } else {
            plotWrapper.style.removeProperty('maxHeight');
        }
        plotWrapper.style.height = '';
        plotWrapper.style.aspectRatio = sizing?.aspectRatio || '';

        const plotCanvas = document.createElement('div');
        plotCanvas.id = plotId;
        plotCanvas.className = 'chart-plot-canvas';
        plotCanvas.style.width = '100%';
        plotCanvas.style.height = '100%';
        plotWrapper.appendChild(plotCanvas);

        card.appendChild(header);
        card.appendChild(plotWrapper);
        elements.chartsGrid.appendChild(card);

        const figure = buildFigure(chart);
        if (figure) {
            const config = {
                responsive: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'autoScale2d']
            };

            Plotly.newPlot(plotCanvas, figure.data, figure.layout, config).then(() => {
                try { Plotly.Plots.resize(plotCanvas); } catch (error) { /* noop */ }
            });

            if (window.ResizeObserver) {
                try {
                    const observer = new ResizeObserver(() => {
                        try { Plotly.Plots.resize(plotCanvas); } catch (resizeError) { /* noop */ }
                    });
                    observer.observe(plotWrapper);
                    state.resizeObservers.set(chart.id, observer);
                } catch (error) {
                    window.addEventListener('resize', () => {
                        try { Plotly.Plots.resize(plotCanvas); } catch (resizeError) { /* noop */ }
                    }, { passive: true });
                }
            }
        } else {
            plotCanvas.className = 'chart-plot-canvas flex items-center justify-center text-sm text-white/60 text-center px-4';
            plotCanvas.textContent = 'Nao foi possivel renderizar este grafico.';
        }
    });

    if (state.currentViewId !== null) {
        const currentChart = state.charts.find((item) => item.id === state.currentViewId);
        if (!currentChart) {
            closeViewModal();
            updateViewModalNavigation();
        } else if (isViewModalOpen()) {
            updateViewModalContent(currentChart);
            renderViewModalChart(currentChart);
        } else {
            updateViewModalNavigation();
        }
    } else {
        updateViewModalNavigation();
    }
}

function refreshCharts() {
    fetch(ctx.endpoints.list)
        .then((response) => response.json())
        .then((data) => {
            state.charts = Array.isArray(data) ? data : [];
            renderCharts();
            showToast('Galeria atualizada.', 'success');
        })
        .catch(() => showToast('Nao foi possivel atualizar os graficos.', 'error'));
}

function openDeleteChartModal(chartId, chartName) {
    state.pendingDelete = chartId;
    elements.deleteName.textContent = chartName;
    elements.deleteModal.classList.remove('hidden');
    elements.deleteModal.classList.add('flex');
}

function closeDeleteChartModal() {
    state.pendingDelete = null;
    elements.deleteName.textContent = '';
    elements.deleteModal.classList.add('hidden');
    elements.deleteModal.classList.remove('flex');
}

function handleChartDeletion() {
    if (!state.pendingDelete) {
        closeDeleteChartModal();
        return;
    }

    const endpoint = ctx.endpoints.deleteTemplate.replace(/0$/, String(state.pendingDelete));
    elements.confirmDeleteBtn.disabled = true;
    elements.confirmDeleteBtn.classList.add('opacity-70', 'cursor-not-allowed');

    fetch(endpoint, { method: 'DELETE' })
        .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok) {
                throw new Error(data.error || 'Erro ao excluir grafico.');
            }
            state.charts = state.charts.filter((chart) => chart.id !== state.pendingDelete);
            renderCharts();
            closeDeleteChartModal();
            showToast(data.message || 'Grafico excluido com sucesso.', 'success');
        })
        .catch((error) => showToast(error.message, 'error'))
        .finally(() => {
            elements.confirmDeleteBtn.disabled = false;
            elements.confirmDeleteBtn.classList.remove('opacity-70', 'cursor-not-allowed');
        });
}

function createThemeMenu() {
    if (document.getElementById('themeMenuContainer')) {
        return;
    }

    if (!document.getElementById('menuPortal')) return;

    const menuContainer = document.createElement('div');
    menuContainer.id = 'themeMenuContainer';
    Object.assign(menuContainer.style, {
        position: 'fixed',
        top: '0',
        left: '0',
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: '99999'
    });
    document.body.appendChild(menuContainer);

    const menu = document.createElement('div');
    menu.id = 'themeMenu';
    menu.className = `hidden ${ctx.themeClasses?.modalSurface || ''} rounded-lg shadow-xl py-1 w-56`;
    menu.style.position = 'absolute';
    menu.style.pointerEvents = 'auto';

    const themes = [
        { name: 'Escuro', value: 'dark', preview: 'bg-gradient-to-r from-gray-900 via-gray-800 to-gray-700' },
        { name: 'Claro', value: 'light', preview: 'bg-gradient-to-r from-blue-500 via-white to-gray-100' },
        { name: 'Neon', value: 'neon', preview: 'bg-gradient-to-r from-purple-600 via-green-400 to-black' },
        { name: 'Futurista', value: 'futurist', preview: 'bg-gradient-to-r from-blue-600 via-cyan-400 to-purple-600' }
    ];

    themes.forEach((option) => {
        const link = document.createElement('a');
        link.href = '#';
        link.className = 'block px-4 py-2 text-sm flex items-center justify-between hover:opacity-80 transition';

        const content = document.createElement('div');
        content.className = 'flex items-center gap-3';

        const name = document.createElement('span');
        name.textContent = option.name;

        const preview = document.createElement('div');
        preview.className = `w-5 h-5 rounded-full ${option.preview} border border-gray-400/20`;

        content.appendChild(preview);
        content.appendChild(name);
        link.appendChild(content);

        link.addEventListener('click', (event) => {
            event.preventDefault();
            changeTheme(option.value);
            menu.classList.add('hidden');
        });

        menu.appendChild(link);
    });

    menuContainer.appendChild(menu);
}

function changeTheme(theme) {
    fetch(`/theme/${theme}`, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
        .then((response) => {
            if (response.ok) {
                window.location.reload();
            }
        });
}

function toggleThemeMenu(event) {
    const menu = document.getElementById('themeMenu');
    if (!menu) return;

    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const menuHeight = 220;
    const menuWidth = 240;

    if (menu.classList.contains('hidden')) {
        let top = rect.top;
        let left = rect.right + 12;

        if (rect.top + menuHeight > viewportHeight) {
            top = Math.max(16, rect.bottom - menuHeight);
        }

        if (left + menuWidth > viewportWidth) {
            left = Math.max(16, rect.left - menuWidth - 12);
        }

        menu.style.top = `${top}px`;
        menu.style.left = `${left}px`;
        menu.classList.remove('hidden');
    } else {
        menu.classList.add('hidden');
    }
}

function bindGlobalListeners() {
    document.addEventListener('click', (event) => {
        const menu = document.getElementById('themeMenu');
        if (menu && !menu.classList.contains('hidden')) {
            const isThemeButton = event.target.closest('button[title="Alterar Tema"]');
            if (!isThemeButton && !menu.contains(event.target)) {
                menu.classList.add('hidden');
            }
        }

        if (state.activeDropdown) {
            const dropdown = state.activeDropdown === 'indicator' ? elements.indicatorDropdown : elements.metricDropdown;
            const toggle = state.activeDropdown === 'indicator' ? elements.indicatorToggle : elements.metricToggle;
            if (dropdown && !dropdown.contains(event.target) && !toggle.contains(event.target)) {
                closeAllDropdowns();
            }
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeAllDropdowns();
            if (elements.chartModal && !elements.chartModal.classList.contains('hidden')) {
                closeChartModal();
            }
            if (elements.deleteModal && !elements.deleteModal.classList.contains('hidden')) {
                closeDeleteChartModal();
            }
            if (elements.viewModal && !elements.viewModal.classList.contains('hidden')) {
                closeViewModal();
            }
        }
    });
}

function bindEventListeners() {
    elements.openModalBtn?.addEventListener('click', openChartModal);
    elements.refreshBtn?.addEventListener('click', refreshCharts);
    elements.chartForm?.addEventListener('submit', handleChartSubmit);

    elements.metricToggle?.addEventListener('click', (event) => {
        event.stopPropagation();
        toggleDropdown('metric');
    });
    elements.indicatorToggle?.addEventListener('click', (event) => {
        event.stopPropagation();
        toggleDropdown('indicator');
    });

    elements.metricDropdown?.addEventListener('click', (event) => event.stopPropagation());
    elements.indicatorDropdown?.addEventListener('click', (event) => event.stopPropagation());

    document.getElementById('closeChartModalBtn')?.addEventListener('click', closeChartModal);
    document.getElementById('cancelChartBtn')?.addEventListener('click', closeChartModal);

    elements.chartModal?.addEventListener('click', (event) => {
        if (event.target.id === 'chartModal') {
            closeChartModal();
        }
    });

    elements.chartsGrid?.addEventListener('click', (event) => {
        const viewBtn = event.target.closest('button[data-view-chart]');
        if (viewBtn) {
            const chartId = Number.parseInt(viewBtn.dataset.viewChart, 10);
            const chart = state.charts.find((item) => item.id === chartId);
            if (chart) {
                openViewModal(chart);
            }
            return;
        }

        const deleteBtn = event.target.closest('button[data-delete-chart]');
        if (!deleteBtn) return;
        const chartId = Number.parseInt(deleteBtn.dataset.deleteChart, 10);
        const chartName = deleteBtn.dataset.chartName || 'este grafico';
        openDeleteChartModal(chartId, chartName);
    });

    elements.cancelDeleteBtn?.addEventListener('click', closeDeleteChartModal);
    elements.confirmDeleteBtn?.addEventListener('click', handleChartDeletion);

    elements.deleteModal?.addEventListener('click', (event) => {
        if (event.target.id === 'chartDeleteModal') {
            closeDeleteChartModal();
        }
    });

    elements.closeViewModalBtn?.addEventListener('click', closeViewModal);
    elements.nextViewModalBtn?.addEventListener('click', showNextViewChart);

    elements.viewModal?.addEventListener('click', (event) => {
        if (event.target.id === 'viewChartModal' || event.target.id === 'viewChartModalOverlay') {
            closeViewModal();
        }
    });
}

function init() {
    window.logout = logout;
    window.openChartModal = openChartModal;
    window.toggleThemeMenu = toggleThemeMenu;

    populateMetricOptions(true);
    populateIndicatorOptions(true);
    updateColorPickers();
    createThemeMenu();
    renderCharts();
    bindEventListeners();
    bindGlobalListeners();

    if (!indicatorMap.size && elements.openModalBtn) {
        elements.openModalBtn.disabled = true;
        elements.openModalBtn.classList.add('opacity-60', 'cursor-not-allowed');
    }
}

document.addEventListener('DOMContentLoaded', init);
