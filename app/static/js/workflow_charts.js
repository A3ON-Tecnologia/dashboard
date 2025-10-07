(function () {
    const context = window.__CHARTS_CONTEXT__ || null;
    if (!context) {
        return;
    }

    const state = {
        currentStep: 1,
        editingChartId: null,
        selectedChartType: null,
        charts: [],
        datasetCache: new Map(),
        chartInstances: new Map(),
        previewInstance: null,
        series: [],
        labelField: '',
        chartName: '',
        category: '',
        options: {
            stacked: false,
            smooth: false,
        },
        datasetMeta: null,
        loadingCharts: false,
    };

    const chartTypes = [
        {
            id: 'bar',
            title: 'Barras verticais',
            description: 'Compare indicadores e períodos lado a lado.',
            icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18m18 0H3m3-6h2m3-8h2m3 4h2" /></svg>',
        },
        {
            id: 'bar-horizontal',
            title: 'Barras horizontais',
            description: 'Realce comparações com orientação horizontal.',
            icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18m18 0H3m4-4h8m-8-5h11m-11-5h6" /></svg>',
        },
        {
            id: 'line',
            title: 'Linha',
            description: 'Acompanhe tendências e evolução ao longo do tempo.',
            icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18m18 0H3m3-6 4-4 3 3 5-7" /></svg>',
        },
        {
            id: 'area',
            title: 'Área',
            description: 'Visualize o preenchimento acumulado entre séries.',
            icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18m18 0H3m3-6 4-6 3 5 5-9v10H6" /></svg>',
        },
        {
            id: 'pie',
            title: 'Pizza',
            description: 'Mostre a composição percentual de um indicador.',
            icon: '<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 3.084a9 9 0 0 1 9.666 9.666M12 21a9 9 0 1 1 0-18v9l6.364 6.364A8.963 8.963 0 0 1 12 21Z" /></svg>',
        },
    ];

    const workflowType = context.workflowType;
    const defaultPalette = Array.isArray(context.chartPalette) ? context.chartPalette : ['#38bdf8', '#a855f7', '#22d3ee', '#f472b6', '#facc15', '#34d399'];

    const elements = {
        openModal: document.getElementById('openCreateChartBtn'),
        refresh: document.getElementById('refreshChartsBtn'),
        modal: document.getElementById('chartModal'),
        modalPanel: document.querySelector('#chartModal [data-modal-panel]'),
        modalBackdrop: document.querySelector('#chartModal [data-modal-backdrop]'),
        closeModal: document.getElementById('closeChartModal'),
        modalTitle: document.getElementById('chartModalTitle'),
        stepIndicators: document.querySelectorAll('[data-step-indicator]'),
        stepSections: document.querySelectorAll('[data-chart-step]'),
        chartTypeOptions: document.getElementById('chartTypeOptions'),
        chartLabelField: document.getElementById('chartLabelField'),
        chartNameInput: document.getElementById('chartNameInput'),
        chartCategoryWrapper: document.getElementById('analiseCategoryWrapper'),
        chartCategorySelect: document.getElementById('chartCategory'),
        chartCategoryHint: document.getElementById('chartCategoryHint'),
        addSeriesBtn: document.getElementById('addSeriesBtn'),
        seriesContainer: document.getElementById('seriesContainer'),
        advancedOptions: document.getElementById('chartAdvancedOptions'),
        prevStep: document.getElementById('chartPrevStep'),
        nextStep: document.getElementById('chartNextStep'),
        saveBtn: document.getElementById('chartSaveBtn'),
        editDataStep: document.getElementById('editDataStep'),
        modalErrors: document.getElementById('chartModalErrors'),
        previewCanvas: document.getElementById('chartPreviewCanvas'),
        previewMetadata: document.getElementById('previewMetadata'),
        emptyState: document.getElementById('chartsEmptyState'),
        grid: document.getElementById('chartsGrid'),
        feedback: document.getElementById('chartFeedback'),
    };

    function clearModalErrors() {
        if (!elements.modalErrors) return;
        elements.modalErrors.classList.add('hidden');
        elements.modalErrors.textContent = '';
    }

    function showModalError(message) {
        if (!elements.modalErrors) return;
        elements.modalErrors.textContent = message;
        elements.modalErrors.classList.remove('hidden');
    }

    function setFeedback(message, tone = 'neutral') {
        if (!elements.feedback) return;
        if (!message) {
            elements.feedback.classList.add('hidden');
            elements.feedback.textContent = '';
            return;
        }
        const toneClass = tone === 'error'
            ? 'text-rose-300'
            : tone === 'success'
                ? 'text-emerald-300'
                : 'text-white/60';
        elements.feedback.className = `text-sm ${toneClass}`;
        elements.feedback.textContent = message;
        elements.feedback.classList.remove('hidden');
    }

    function beautifyLabel(value) {
        if (!value) return '';
        return String(value)
            .replace(/_/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
            .replace(/\b\w/g, char => char.toUpperCase());
    }

    function getDefaultColor(index) {
        if (!defaultPalette.length) {
            return '#38bdf8';
        }
        return defaultPalette[index % defaultPalette.length];
    }

    function openModal(editingChart = null) {
        if (!elements.modal || !elements.modalPanel) return;

        state.currentStep = 1;
        state.editingChartId = editingChart ? editingChart.id : null;
        state.selectedChartType = editingChart ? editingChart.chart_type : null;
        state.series = editingChart ? editingChart.series.map((serie, index) => ({
            id: `${Date.now()}_${index}`,
            label: serie.label || '',
            value_key: serie.value_key || '',
            color: serie.color || getDefaultColor(index),
        })) : [];
        state.labelField = editingChart ? editingChart.label_key : '';
        state.chartName = editingChart ? editingChart.name : '';
        state.options.stacked = Boolean(editingChart && editingChart.options && editingChart.options.stacked);
        state.options.smooth = Boolean(editingChart && editingChart.options && editingChart.options.tension);
        state.category = editingChart && editingChart.source_type === 'analise_jp' ? editingChart.source_id : '';

        clearModalErrors();

        if (!state.series.length) {
            addSeries();
        } else {
            renderSeries();
        }

        renderChartTypeChoices();
        renderAdvancedOptions();
        populateCategorySelect();

        if (state.labelField) {
            elements.chartLabelField.value = state.labelField;
        } else {
            elements.chartLabelField.value = '';
        }
        elements.chartNameInput.value = state.chartName || '';

        goToStep(1);

        elements.modal.classList.remove('hidden');
        requestAnimationFrame(() => {
            elements.modalBackdrop.style.opacity = '1';
            elements.modalPanel.classList.remove('modal-leave');
            elements.modalPanel.classList.add('modal-enter');
            elements.modalPanel.style.opacity = '1';
            elements.modalPanel.style.transform = 'scale(1) translateY(0)';
        });

        if (editingChart) {
            elements.modalTitle.textContent = 'Editar gráfico';
            if (workflowType === 'analise_jp' && state.category) {
                ensureDataset(state.category).then(() => {
                    elements.chartLabelField.value = state.labelField || '';
                    renderSeries();
                }).catch(() => {
                    showModalError('Não foi possível carregar os dados da categoria selecionada.');
                });
            } else if (workflowType === 'balancete') {
                ensureDataset('latest').then(() => {
                    elements.chartLabelField.value = state.labelField || '';
                    renderSeries();
                }).catch(() => {
                    showModalError('Não foi possível carregar o dataset deste workflow.');
                });
            }
        } else {
            elements.modalTitle.textContent = 'Criar gráfico';
            if (workflowType === 'balancete') {
                ensureDataset('latest').then(() => {
                    if (!state.labelField) {
                        const firstLabel = state.datasetMeta && state.datasetMeta.labelOptions.length
                            ? state.datasetMeta.labelOptions[0].key
                            : '';
                        state.labelField = firstLabel;
                        elements.chartLabelField.value = firstLabel;
                    }
                }).catch(() => {
                    showModalError('Nenhum dado disponível para criar gráficos. Faça um upload primeiro.');
                });
            }
        }
    }

    function closeModal() {
        if (!elements.modal || !elements.modalPanel) return;
        if (state.previewInstance) {
            state.previewInstance.destroy();
            state.previewInstance = null;
        }
        elements.modalPanel.classList.remove('modal-enter');
        elements.modalPanel.classList.add('modal-leave');
        elements.modalBackdrop.style.opacity = '0';
        setTimeout(() => {
            elements.modal.classList.add('hidden');
            elements.modalPanel.classList.remove('modal-leave');
            elements.modalPanel.style.opacity = '0';
            elements.modalPanel.style.transform = 'scale(0.95) translateY(20px)';
        }, 180);
    }

    function goToStep(step) {
        state.currentStep = step;
        elements.stepIndicators.forEach((indicator) => {
            const stepIndex = Number(indicator.getAttribute('data-step-indicator'));
            if (stepIndex === step) {
                indicator.classList.add('bg-white/10', 'text-white');
            } else {
                indicator.classList.remove('bg-white/10', 'text-white');
            }
        });
        elements.stepSections.forEach((section) => {
            const stepIndex = Number(section.getAttribute('data-chart-step'));
            section.classList.toggle('hidden', stepIndex !== step);
        });

        elements.prevStep.classList.toggle('hidden', step <= 1);
        elements.nextStep.classList.toggle('hidden', step >= 3);
        elements.saveBtn.classList.toggle('hidden', step !== 3);
        clearModalErrors();
    }

    function renderChartTypeChoices() {
        if (!elements.chartTypeOptions) return;
        elements.chartTypeOptions.innerHTML = '';
        chartTypes.forEach((chartType) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'flex items-start gap-3 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-4 hover:border-emerald-400/60 hover:bg-white/10 transition-colors';
            if (state.selectedChartType === chartType.id) {
                button.classList.add('border-emerald-400/70', 'bg-white/10');
            }
            button.innerHTML = `
                <span class="flex-shrink-0 w-10 h-10 rounded-2xl bg-white/10 border border-white/10 flex items-center justify-center text-white/70">${chartType.icon}</span>
                <span class="text-left space-y-1">
                    <span class="block text-sm font-semibold text-white">${chartType.title}</span>
                    <span class="block text-xs text-white/60">${chartType.description}</span>
                </span>
            `;
            button.addEventListener('click', () => {
                state.selectedChartType = chartType.id;
                renderChartTypeChoices();
                renderAdvancedOptions();
            });
            elements.chartTypeOptions.appendChild(button);
        });
    }

    function populateCategorySelect() {
        if (workflowType !== 'analise_jp' || !elements.chartCategorySelect) {
            if (elements.chartCategoryWrapper) {
                elements.chartCategoryWrapper.classList.add('hidden');
            }
            return;
        }
        elements.chartCategoryWrapper.classList.remove('hidden');
        elements.chartCategorySelect.innerHTML = '';
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Selecione a categoria';
        elements.chartCategorySelect.appendChild(placeholder);

        const categories = Array.isArray(context.categoriesMeta) ? context.categoriesMeta : [];
        categories.forEach((category) => {
            const option = document.createElement('option');
            option.value = category.slug;
            option.textContent = `${category.label}${category.has_data ? '' : ' (sem dados)'}`;
            elements.chartCategorySelect.appendChild(option);
        });

        if (state.category) {
            elements.chartCategorySelect.value = state.category;
            updateCategoryHint();
        }
    }

    function updateCategoryHint(meta = null) {
        if (!elements.chartCategoryHint) return;
        const categories = Array.isArray(context.categoriesMeta) ? context.categoriesMeta : [];
        const current = meta || categories.find((item) => item.slug === state.category);
        if (!current) {
            elements.chartCategoryHint.textContent = '';
            return;
        }
        if (!current.has_data) {
            elements.chartCategoryHint.textContent = 'Nenhum upload visível para esta categoria. Adicione dados para gerar o gráfico.';
            elements.chartCategoryHint.className = 'text-xs text-amber-300';
        } else {
            elements.chartCategoryHint.textContent = `Último upload: ${current.latest_upload && current.latest_upload.created_at ? new Date(current.latest_upload.created_at).toLocaleDateString('pt-BR') : 'recentemente'} • Registros disponíveis: ${current.record_count}`;
            elements.chartCategoryHint.className = 'text-xs text-white/50';
        }
    }

    function addSeries(initialData) {
        const baseIndex = state.series.length;
        const serie = {
            id: `${Date.now()}_${Math.random().toString(16).slice(2)}`,
            label: initialData && initialData.label ? initialData.label : '',
            value_key: initialData && initialData.value_key ? initialData.value_key : '',
            color: initialData && initialData.color ? initialData.color : getDefaultColor(baseIndex),
        };
        state.series.push(serie);
        renderSeries();
    }

    function removeSeries(id) {
        if (state.series.length <= 1) {
            showModalError('Inclua pelo menos uma série.');
            return;
        }
        state.series = state.series.filter((serie) => serie.id !== id);
        renderSeries();
    }

    function renderSeries() {
        if (!elements.seriesContainer) return;
        elements.seriesContainer.innerHTML = '';
        state.series.forEach((serie, index) => {
            const row = document.createElement('div');
            row.className = 'grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-4 items-center';

            const labelWrapper = document.createElement('div');
            labelWrapper.className = 'space-y-2';
            const labelInputLabel = document.createElement('label');
            labelInputLabel.className = 'text-xs uppercase tracking-widest text-white/50';
            labelInputLabel.textContent = 'Nome da série';
            const labelInput = document.createElement('input');
            labelInput.type = 'text';
            labelInput.className = 'w-full rounded-xl bg-white/10 border border-white/10 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400';
            labelInput.value = serie.label;
            labelInput.placeholder = `Série ${index + 1}`;
            labelInput.addEventListener('input', () => {
                serie.label = labelInput.value;
            });
            labelWrapper.appendChild(labelInputLabel);
            labelWrapper.appendChild(labelInput);

            const valueWrapper = document.createElement('div');
            valueWrapper.className = 'space-y-2';
            const valueLabel = document.createElement('label');
            valueLabel.className = 'text-xs uppercase tracking-widest text-white/50';
            valueLabel.textContent = 'Coluna de valores';
            const valueSelect = document.createElement('select');
            valueSelect.className = 'w-full rounded-xl bg-white/10 border border-white/10 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400';
            valueSelect.appendChild(new Option('Selecione', ''));
            const valueOptions = state.datasetMeta ? state.datasetMeta.valueOptions : [];
            valueOptions.forEach((option) => {
                const opt = new Option(option.label, option.key);
                valueSelect.appendChild(opt);
            });
            valueSelect.value = serie.value_key || '';
            valueSelect.addEventListener('change', () => {
                serie.value_key = valueSelect.value;
            });
            valueWrapper.appendChild(valueLabel);
            valueWrapper.appendChild(valueSelect);

            const colorWrapper = document.createElement('div');
            colorWrapper.className = 'flex flex-col md:items-end gap-2';
            const colorLabel = document.createElement('label');
            colorLabel.className = 'text-xs uppercase tracking-widest text-white/50';
            colorLabel.textContent = 'Cor';
            const colorInput = document.createElement('input');
            colorInput.type = 'color';
            colorInput.className = 'w-16 h-10 rounded-xl border border-white/10 bg-white/10 cursor-pointer';
            colorInput.value = serie.color || getDefaultColor(index);
            colorInput.addEventListener('input', () => {
                serie.color = colorInput.value;
            });
            colorWrapper.appendChild(colorLabel);
            colorWrapper.appendChild(colorInput);

            if (state.series.length > 1) {
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'text-xs uppercase tracking-widest px-3 py-1.5 rounded-full border border-white/10 hover:border-rose-400 hover:text-rose-300 transition-colors';
                removeBtn.textContent = 'Remover';
                removeBtn.addEventListener('click', () => removeSeries(serie.id));
                colorWrapper.appendChild(removeBtn);
            }

            row.appendChild(labelWrapper);
            row.appendChild(valueWrapper);
            row.appendChild(colorWrapper);
            elements.seriesContainer.appendChild(row);
        });
    }

    function renderAdvancedOptions() {
        if (!elements.advancedOptions) return;
        elements.advancedOptions.innerHTML = '';
        const type = state.selectedChartType;
        if (!type) return;

        if (type === 'bar' || type === 'bar-horizontal' || type === 'area') {
            const stackedWrapper = document.createElement('label');
            stackedWrapper.className = 'flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 cursor-pointer';
            const stackedCheckbox = document.createElement('input');
            stackedCheckbox.type = 'checkbox';
            stackedCheckbox.checked = state.options.stacked;
            stackedCheckbox.className = 'w-4 h-4 rounded border-white/20 bg-white/10';
            stackedCheckbox.addEventListener('change', () => {
                state.options.stacked = stackedCheckbox.checked;
            });
            const stackedText = document.createElement('span');
            stackedText.className = 'text-sm text-white/70';
            stackedText.textContent = 'Empilhar séries';
            stackedWrapper.appendChild(stackedCheckbox);
            stackedWrapper.appendChild(stackedText);
            elements.advancedOptions.appendChild(stackedWrapper);
        }

        if (type === 'line' || type === 'area') {
            const smoothWrapper = document.createElement('label');
            smoothWrapper.className = 'flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 cursor-pointer';
            const smoothCheckbox = document.createElement('input');
            smoothCheckbox.type = 'checkbox';
            smoothCheckbox.checked = state.options.smooth;
            smoothCheckbox.className = 'w-4 h-4 rounded border-white/20 bg-white/10';
            smoothCheckbox.addEventListener('change', () => {
                state.options.smooth = smoothCheckbox.checked;
            });
            const smoothText = document.createElement('span');
            smoothText.className = 'text-sm text-white/70';
            smoothText.textContent = 'Suavizar linhas';
            smoothWrapper.appendChild(smoothCheckbox);
            smoothWrapper.appendChild(smoothText);
            elements.advancedOptions.appendChild(smoothWrapper);
        }
    }

    function normaliseNumeric(value) {
        if (typeof value === 'number') {
            return Number.isFinite(value) ? value : null;
        }
        if (typeof value === 'string') {
            const normalised = value.replace(/\./g, '').replace(',', '.').replace(/[^0-9.-]/g, '');
            const parsed = Number.parseFloat(normalised);
            return Number.isFinite(parsed) ? parsed : null;
        }
        return null;
    }

    function inferFieldTypes(records, fields) {
        return fields.map((field) => {
            let numeric = false;
            for (const record of records) {
                if (!record || typeof record !== 'object') {
                    continue;
                }
                const value = record[field];
                if (value === undefined || value === null || value === '') {
                    continue;
                }
                const parsed = normaliseNumeric(value);
                if (parsed === null) {
                    numeric = false;
                    break;
                }
                numeric = true;
            }
            return { key: field, label: beautifyLabel(field), type: numeric ? 'number' : 'text' };
        });
    }

    function normaliseDataset(sourceType, payload) {
        if (!payload || typeof payload !== 'object') {
            return { records: [], labelOptions: [], valueOptions: [], meta: {} };
        }
        if (sourceType === 'balancete') {
            const records = Array.isArray(payload.records) ? payload.records : [];
            const labelFields = Array.isArray(payload.label_fields) ? payload.label_fields : [];
            const valueFields = Array.isArray(payload.value_fields) ? payload.value_fields : [];
            const labelOptions = labelFields.map((field) => ({ key: field, label: beautifyLabel(field) }));
            const valueOptions = valueFields.map((field) => ({ key: field.key, label: field.label || beautifyLabel(field.key), type: 'number' }));
            return { records, labelOptions, valueOptions, meta: payload.meta || {} };
        }

        const records = Array.isArray(payload.records) ? payload.records : [];
        const fields = Array.isArray(payload.fields) ? payload.fields : [];
        const inferred = inferFieldTypes(records, fields);
        const labelOptions = inferred.map((field) => ({ key: field.key, label: field.label }));
        const valueOptions = inferred.filter((field) => field.type === 'number');
        return { records, labelOptions, valueOptions, meta: { categoria: payload.categoria } };
    }

    async function ensureDataset(sourceId, updateState = true) {
        const sourceType = workflowType === 'analise_jp' ? 'analise_jp' : 'balancete';
        const cacheKey = `${sourceType}:${sourceId}`;
        if (state.datasetCache.has(cacheKey)) {
            const cached = state.datasetCache.get(cacheKey);
            if (updateState) {
                state.datasetMeta = cached;
                populateLabelAndSeriesDefaults();
            }
            return cached;
        }

        let endpoint = null;
        if (sourceType === 'balancete') {
            endpoint = context.endpoints.dataset;
        } else {
            const pattern = context.endpoints.analiseDataset;
            endpoint = pattern ? pattern.replace('__categoria__', encodeURIComponent(sourceId)) : null;
        }

        if (!endpoint) {
            throw new Error('Dataset indisponível');
        }

        const response = await fetch(endpoint, { headers: { 'Accept': 'application/json' } });
        if (!response.ok) {
            throw new Error('Falha ao carregar dados');
        }
        const payload = await response.json();
        const meta = normaliseDataset(sourceType, payload);
        state.datasetCache.set(cacheKey, meta);
        if (updateState) {
            state.datasetMeta = meta;
            populateLabelAndSeriesDefaults();
        }
        return meta;
    }

    function populateLabelAndSeriesDefaults() {
        if (!state.datasetMeta) return;
        if (!state.labelField) {
            state.labelField = state.datasetMeta.labelOptions.length ? state.datasetMeta.labelOptions[0].key : '';
            elements.chartLabelField.value = state.labelField;
        }

        const currentOptions = state.datasetMeta.valueOptions;
        state.series.forEach((serie, index) => {
            if (!serie.value_key && currentOptions[index]) {
                serie.value_key = currentOptions[index].key;
            }
        });
        renderSeries();

        elements.chartLabelField.innerHTML = '';
        state.datasetMeta.labelOptions.forEach((option) => {
            const opt = new Option(option.label, option.key);
            elements.chartLabelField.appendChild(opt);
        });
        elements.chartLabelField.value = state.labelField || '';
    }

    function validateStep(step) {
        if (step === 1) {
            if (!state.selectedChartType) {
                showModalError('Escolha um tipo de gráfico para continuar.');
                return false;
            }
            clearModalErrors();
            return true;
        }

        if (step === 2) {
            clearModalErrors();
            state.chartName = elements.chartNameInput.value.trim();
            state.labelField = elements.chartLabelField.value;
            if (!state.chartName) {
                showModalError('Informe um nome para o gráfico.');
                return false;
            }
            if (!state.labelField) {
                showModalError('Selecione a coluna que será utilizada como rótulo.');
                return false;
            }
            const filledSeries = state.series.filter((serie) => serie.value_key);
            if (!filledSeries.length) {
                showModalError('Adicione pelo menos uma série com coluna de valores.');
                return false;
            }
            if (state.selectedChartType === 'pie' && filledSeries.length > 1) {
                showModalError('Gráficos de pizza suportam apenas uma série.');
                return false;
            }
            if (workflowType === 'analise_jp') {
                state.category = elements.chartCategorySelect.value;
                if (!state.category) {
                    showModalError('Selecione a categoria que servirá de origem dos dados.');
                    return false;
                }
            }
            clearModalErrors();
            return true;
        }

        return true;
    }

    function buildChartPayload() {
        const payload = {
            name: state.chartName,
            chart_type: state.selectedChartType,
            label_key: state.labelField,
            series: state.series.map((serie) => ({
                label: serie.label || serie.value_key,
                value_key: serie.value_key,
                color: serie.color,
            })).filter((serie) => serie.value_key),
        };

        if (workflowType === 'analise_jp') {
            payload.source_id = state.category;
        } else {
            payload.source_id = 'latest';
        }

        if (state.selectedChartType === 'bar-horizontal') {
            payload.orientation = 'horizontal';
        }
        if (state.options.stacked) {
            payload.stacked = true;
        }
        if (state.selectedChartType === 'area') {
            payload.fill_mode = 'origin';
        }
        if (state.options.smooth && (state.selectedChartType === 'line' || state.selectedChartType === 'area')) {
            payload.tension = 0.35;
        }
        return payload;
    }

    function buildChartConfiguration(chart, datasetMeta) {
        const chartType = chart.chart_type === 'area' ? 'line' : chart.chart_type === 'bar-horizontal' ? 'bar' : chart.chart_type;
        const labels = datasetMeta.records.map((record) => record[chart.label_key] || '-');
        const datasets = chart.series.map((serie, index) => {
            const values = datasetMeta.records.map((record) => normaliseNumeric(record[serie.value_key]));
            const baseColor = serie.color || getDefaultColor(index);
            const datasetConfig = {
                label: serie.label || beautifyLabel(serie.value_key),
                data: values,
                backgroundColor: chart.chart_type === 'pie' ? values.map((_, idx) => serie.color || getDefaultColor(idx)) : baseColor,
                borderColor: baseColor,
                borderWidth: chart.chart_type === 'line' || chart.chart_type === 'area' ? 2 : 1.5,
                tension: chart.options && chart.options.tension ? Number(chart.options.tension) : 0,
                fill: chart.chart_type === 'area',
            };
            return datasetConfig;
        });

        const config = {
            type: chartType === 'pie' ? 'pie' : chartType,
            data: {
                labels,
                datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#cbd5f5',
                            font: {
                                family: 'Space Grotesk',
                            },
                        },
                    },
                    tooltip: {
                        callbacks: {},
                    },
                },
                scales: {},
            },
        };

        if (chart.chart_type === 'bar-horizontal') {
            config.options.indexAxis = 'y';
        }

        if (chart.options && chart.options.stacked) {
            config.options.scales.x = config.options.scales.x || {};
            config.options.scales.y = config.options.scales.y || {};
            config.options.scales.x.stacked = true;
            config.options.scales.y.stacked = true;
        }

        if (chartType !== 'pie') {
            config.options.scales.x = config.options.scales.x || { ticks: { color: '#cbd5f5' }, grid: { color: 'rgba(148, 163, 184, 0.15)' } };
            config.options.scales.y = config.options.scales.y || { ticks: { color: '#cbd5f5' }, grid: { color: 'rgba(148, 163, 184, 0.12)' } };
        }

        if (chart.chart_type === 'pie') {
            config.options.plugins.legend.position = 'bottom';
        }

        return config;
    }

    function renderPreview() {
        if (!state.datasetMeta) {
            showModalError('Dataset indisponível para gerar a pré-visualização.');
            return;
        }
        const payload = buildChartPayload();
        const chartConfig = {
            id: state.editingChartId || 'preview',
            name: payload.name,
            chart_type: payload.chart_type,
            label_key: payload.label_key,
            series: payload.series,
            options: {
                stacked: payload.stacked,
                fill_mode: payload.fill_mode,
                tension: payload.tension,
            },
        };
        if (state.previewInstance) {
            state.previewInstance.destroy();
        }
        const config = buildChartConfiguration(chartConfig, state.datasetMeta);
        state.previewInstance = new window.Chart(elements.previewCanvas.getContext('2d'), config);
        if (elements.previewMetadata) {
            elements.previewMetadata.textContent = `Total de registros: ${state.datasetMeta.records.length}`;
        }
    }

    function destroyChartInstance(id) {
        if (state.chartInstances.has(id)) {
            const instance = state.chartInstances.get(id);
            instance.destroy();
            state.chartInstances.delete(id);
        }
    }

    function createChartCard(chart) {
        const card = document.createElement('div');
        card.className = 'glass-panel border border-white/10 rounded-3xl p-6 flex flex-col gap-4 bg-white/5 min-h-[320px]';

        const header = document.createElement('div');
        header.className = 'flex items-start justify-between gap-4';
        const titleWrapper = document.createElement('div');
        const title = document.createElement('h3');
        title.className = 'text-lg font-semibold text-white';
        title.textContent = chart.name;
        const subtitle = document.createElement('p');
        subtitle.className = 'text-xs uppercase tracking-widest text-white/40';
        subtitle.textContent = beautifyLabel(chart.chart_type);
        titleWrapper.appendChild(title);
        titleWrapper.appendChild(subtitle);

        const actions = document.createElement('div');
        actions.className = 'flex items-center gap-2';
        const editBtn = document.createElement('button');
        editBtn.className = 'p-2 rounded-full border border-white/10 hover:border-emerald-400 hover:text-emerald-200 transition-colors';
        editBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 3.487a2.25 2.25 0 1 1 3.182 3.182L7.5 19.213 3 21l1.787-4.5 12.075-13.013z" /></svg>';
        editBtn.addEventListener('click', () => {
            openModal(chart);
        });
        const duplicateBtn = document.createElement('button');
        duplicateBtn.className = 'p-2 rounded-full border border-white/10 hover:border-emerald-400 hover:text-emerald-200 transition-colors';
        duplicateBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 7.5V6a2.25 2.25 0 0 1 2.25-2.25h7.5A2.25 2.25 0 0 1 20.25 6v7.5A2.25 2.25 0 0 1 18 15.75h-1.5M6 8.25H4.5A2.25 2.25 0 0 0 2.25 10.5v7.5A2.25 2.25 0 0 0 4.5 20.25h7.5A2.25 2.25 0 0 0 14.25 18v-1.5" /></svg>';
        duplicateBtn.addEventListener('click', () => duplicateChart(chart));
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'p-2 rounded-full border border-white/10 hover:border-rose-500 hover:text-rose-300 transition-colors';
        deleteBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>';
        deleteBtn.addEventListener('click', () => deleteChart(chart));

        actions.appendChild(editBtn);
        actions.appendChild(duplicateBtn);
        actions.appendChild(deleteBtn);
        header.appendChild(titleWrapper);
        header.appendChild(actions);

        const canvasWrapper = document.createElement('div');
        canvasWrapper.className = 'relative h-64';
        const canvas = document.createElement('canvas');
        canvasWrapper.appendChild(canvas);

        card.appendChild(header);
        card.appendChild(canvasWrapper);

        ensureDataset(chart.source_type === 'analise_jp' ? chart.source_id : 'latest', false).then((datasetMeta) => {
            destroyChartInstance(chart.id);
            const config = buildChartConfiguration(chart, datasetMeta);
            const instance = new window.Chart(canvas.getContext('2d'), config);
            state.chartInstances.set(chart.id, instance);
        }).catch(() => {
            setFeedback('Alguns gráficos não puderam ser carregados. Atualize a página após verificar os dados.', 'error');
        });

        return card;
    }

    function renderCharts() {
        if (!elements.grid || !elements.emptyState) return;
        state.chartInstances.forEach((instance) => instance.destroy());
        state.chartInstances.clear();
        elements.grid.innerHTML = '';
        if (!state.charts.length) {
            elements.emptyState.classList.remove('hidden');
            elements.grid.classList.add('hidden');
            return;
        }
        elements.emptyState.classList.add('hidden');
        elements.grid.classList.remove('hidden');
        state.charts.forEach((chart) => {
            const card = createChartCard(chart);
            elements.grid.appendChild(card);
        });
    }

    async function loadCharts() {
        if (!context.endpoints || !context.endpoints.charts) {
            return;
        }
        state.loadingCharts = true;
        setFeedback('Carregando gráficos...', 'neutral');
        try {
            const response = await fetch(context.endpoints.charts, { headers: { 'Accept': 'application/json' } });
            if (!response.ok) {
                throw new Error('Resposta inválida');
            }
            const payload = await response.json();
            state.charts = Array.isArray(payload.charts) ? payload.charts : [];
            renderCharts();
            if (!state.charts.length) {
                setFeedback('Nenhum gráfico salvo até o momento. Crie sua primeira visualização.', 'neutral');
            } else {
                setFeedback(`${state.charts.length} gráfico(s) carregado(s) com sucesso.`, 'success');
            }
        } catch (error) {
            console.error(error);
            setFeedback('Não foi possível carregar os gráficos. Tente novamente.', 'error');
        } finally {
            state.loadingCharts = false;
        }
    }

    async function saveChart() {
        const payload = buildChartPayload();
        const method = state.editingChartId ? 'PUT' : 'POST';
        const url = state.editingChartId
            ? `${context.endpoints.charts}/${state.editingChartId}`
            : context.endpoints.charts;
        try {
            const response = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Falha ao salvar gráfico.');
            }
            setFeedback(result.message || 'Gráfico salvo com sucesso!', 'success');
            closeModal();
            await loadCharts();
        } catch (error) {
            showModalError(error.message || 'Não foi possível salvar o gráfico.');
        }
    }

    async function duplicateChart(chart) {
        const url = `${context.endpoints.charts}/${chart.id}/duplicate`;
        try {
            const response = await fetch(url, { method: 'POST', headers: { 'Accept': 'application/json' } });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Falha ao duplicar gráfico.');
            }
            setFeedback(result.message || 'Gráfico duplicado!', 'success');
            await loadCharts();
        } catch (error) {
            setFeedback(error.message || 'Não foi possível duplicar o gráfico.', 'error');
        }
    }

    async function deleteChart(chart) {
        if (!window.confirm('Deseja realmente excluir este gráfico?')) {
            return;
        }
        const url = `${context.endpoints.charts}/${chart.id}`;
        try {
            const response = await fetch(url, { method: 'DELETE', headers: { 'Accept': 'application/json' } });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Falha ao remover gráfico.');
            }
            setFeedback(result.message || 'Gráfico removido.', 'success');
            await loadCharts();
        } catch (error) {
            setFeedback(error.message || 'Não foi possível remover o gráfico.', 'error');
        }
    }

    function initialiseEvents() {
        if (elements.openModal) {
            elements.openModal.addEventListener('click', () => openModal());
        }
        if (elements.closeModal) {
            elements.closeModal.addEventListener('click', () => closeModal());
        }
        if (elements.modalBackdrop) {
            elements.modalBackdrop.addEventListener('click', () => closeModal());
        }
        if (elements.refresh) {
            elements.refresh.addEventListener('click', () => loadCharts());
        }
        if (elements.addSeriesBtn) {
            elements.addSeriesBtn.addEventListener('click', () => addSeries());
        }
        if (elements.prevStep) {
            elements.prevStep.addEventListener('click', () => {
                if (state.currentStep > 1) {
                    goToStep(state.currentStep - 1);
                }
            });
        }
        if (elements.nextStep) {
            elements.nextStep.addEventListener('click', async () => {
                if (!validateStep(state.currentStep)) {
                    return;
                }
                if (state.currentStep === 1) {
                    if (workflowType === 'analise_jp') {
                        state.category = elements.chartCategorySelect.value;
                        if (state.category) {
                            try {
                                const dataset = await ensureDataset(state.category);
                                updateCategoryHint();
                                if (!dataset.valueOptions.length) {
                                    showModalError('A categoria selecionada não possui colunas numéricas visíveis. Reveja os dados.');
                                    return;
                                }
                            } catch (error) {
                                showModalError('Não foi possível carregar a categoria selecionada.');
                                return;
                            }
                        }
                    } else {
                        try {
                            await ensureDataset('latest');
                        } catch (error) {
                            showModalError('Nenhum dataset encontrado para este workflow.');
                            return;
                        }
                    }
                }
                if (state.currentStep === 2) {
                    if (workflowType === 'analise_jp' && !state.category) {
                        showModalError('Selecione a categoria para continuar.');
                        return;
                    }
                    try {
                        if (workflowType === 'analise_jp') {
                            await ensureDataset(state.category);
                        } else {
                            await ensureDataset('latest');
                        }
                    } catch (error) {
                        showModalError('Não foi possível preparar o dataset para pré-visualização.');
                        return;
                    }
                    renderPreview();
                }
                goToStep(state.currentStep + 1);
            });
        }
        if (elements.saveBtn) {
            elements.saveBtn.addEventListener('click', () => saveChart());
        }
        if (elements.editDataStep) {
            elements.editDataStep.addEventListener('click', () => goToStep(2));
        }
        if (elements.chartLabelField) {
            elements.chartLabelField.addEventListener('change', () => {
                state.labelField = elements.chartLabelField.value;
            });
        }
        if (elements.chartCategorySelect) {
            elements.chartCategorySelect.addEventListener('change', async () => {
                state.category = elements.chartCategorySelect.value;
                if (!state.category) {
                    return;
                }
                try {
                    const dataset = await ensureDataset(state.category);
                    updateCategoryHint();
                    if (!dataset.valueOptions.length) {
                        showModalError('A categoria selecionada não possui colunas numéricas visíveis.');
                    } else {
                        clearModalErrors();
                    }
                } catch (error) {
                    showModalError('Não foi possível carregar os dados da categoria selecionada.');
                }
            });
        }
    }

    function initialise() {
        if (workflowType === 'balancete') {
            ensureDataset('latest').catch(() => {
                setFeedback('Nenhum dataset disponível. Envie um arquivo para liberar a criação de gráficos.', 'error');
            });
        }
        initialiseEvents();
        renderChartTypeChoices();
        renderAdvancedOptions();
        renderSeries();
        loadCharts();
    }

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !elements.modal.classList.contains('hidden')) {
            closeModal();
        }
    });

    initialise();
})();
