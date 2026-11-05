// ----------------------------------------------------
// Video Studio Pro - Client Script
// ----------------------------------------------------

let currentTask = null;
let currentSilenceData = null;
let currentMode = "auto_silence";

// Cấu hình các mức độ mượt mà khi cắt đoạn thừa
const SMOOTH_PROFILES = {
  ultra_smooth: { min_silence: 1.4, pad: 0.32, merge_gap: 0.7, desc: 'Tự nhiên & Không giật hình' },
  natural: { min_silence: 1.1, pad: 0.28, merge_gap: 0.6, desc: 'Cân bằng & Lưu loát' },
  fast: { min_silence: 0.8, pad: 0.20, merge_gap: 0.4, desc: 'Jump-cut dồn dập kiểu TikTok' }
};
let currentSmoothProfile = 'ultra_smooth';

const smoothPresetsGrid = document.getElementById('smoothPresetsGrid');
const smoothProfileDesc = document.getElementById('smoothProfileDesc');

if (smoothPresetsGrid) {
  smoothPresetsGrid.querySelectorAll('.preset-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      smoothPresetsGrid.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      currentSmoothProfile = chip.dataset.profile || 'ultra_smooth';
      const p = SMOOTH_PROFILES[currentSmoothProfile];
      if (smoothProfileDesc && p) smoothProfileDesc.innerText = p.desc;
      // Tự động quét lại theo độ mượt đã chọn
      analyzeSilences();
    });
  });
}

let targetMb = 18.0;
let progressPollTimer = null;

// DOM Elements
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const btnBrowse = document.getElementById('btnBrowse');
const uploadSection = document.getElementById('uploadSection');
const uploadProgressBox = document.getElementById('uploadProgressBox');
const uploadProgressFill = document.getElementById('uploadProgressFill');
const uploadPercent = document.getElementById('uploadPercent');
const uploadStatusText = document.getElementById('uploadStatusText');

const configSection = document.getElementById('configSection');
const videoCard = document.getElementById('videoCard');
const videoThumb = document.getElementById('videoThumb');
const videoFilename = document.getElementById('videoFilename');
const videoOrigSize = document.getElementById('videoOrigSize');
const videoDuration = document.getElementById('videoDuration');
const videoDimensions = document.getElementById('videoDimensions');
const audioTag = document.getElementById('audioTag');
const btnRemoveFile = document.getElementById('btnRemoveFile');
const workflowSteps = document.querySelectorAll('.workflow-step');
let currentWorkflowStep = 'upload';

function resizeWindowForStep(step) {
  const resize = window.pywebview && window.pywebview.api && window.pywebview.api.resize_for_stage;
  if (resize) resize(step).catch(() => {});
}

function setWorkflowStep(step) {
  currentWorkflowStep = step;
  const order = ['upload', 'configure', 'export'];
  const currentIndex = order.indexOf(step);
  workflowSteps.forEach(item => {
    const itemIndex = order.indexOf(item.dataset.workflowStep);
    item.classList.toggle('active', itemIndex === currentIndex);
    item.classList.toggle('complete', itemIndex < currentIndex);
    item.setAttribute('aria-current', itemIndex === currentIndex ? 'step' : 'false');
  });
  document.body.classList.toggle('workspace-config', step === 'configure');
  document.body.classList.toggle('workspace-export', step === 'export');
  resizeWindowForStep(step);
}

window.addEventListener('pywebviewready', () => resizeWindowForStep(currentWorkflowStep));

// Studio Modular Pipeline Controls
const activeFeaturesCountBadge = document.getElementById('activeFeaturesCountBadge');
const pipelineFlowSteps = document.getElementById('pipelineFlowSteps');

// Module 1: Trim
const cardTrim = document.getElementById('cardTrim');
const toggleTrim = document.getElementById('toggleTrim');
const bodyTrim = document.getElementById('bodyTrim');
const trimPills = document.querySelectorAll('.trim-mode-pill');
const trimSubviews = {
  'auto_silence': document.getElementById('subviewSilence'),
  'intro_outro': document.getElementById('subviewIntro'),
  'manual': document.getElementById('subviewManual')
};
let isTrimEnabled = true;
let currentTrimMode = 'auto_silence';

// Module 2: Bokeh
const cardBokeh = document.getElementById('cardBokeh');
const toggleBokeh = document.getElementById('toggleBokeh');
const bodyBokeh = document.getElementById('bodyBokeh');
let isBokehEnabled = false;

// Module 3: Compress
const cardCompress = document.getElementById('cardCompress');
const toggleCompress = document.getElementById('toggleCompress');
const bodyCompress = document.getElementById('bodyCompress');
let isCompressEnabled = true;

const featureCards = [cardTrim, cardBokeh, cardCompress];

function expandFeatureCard(card) {
  if (!card || card.classList.contains('disabled')) return;
  featureCards.forEach(item => {
    if (!item) return;
    item.classList.toggle('expanded', item === card);
    const header = item.querySelector('.studio-card-header');
    if (header) header.setAttribute('aria-expanded', item === card ? 'true' : 'false');
  });
}

featureCards.forEach(card => {
  const header = card && card.querySelector('.studio-card-header');
  if (!header) return;
  header.setAttribute('role', 'button');
  header.setAttribute('tabindex', '0');
  header.setAttribute('aria-expanded', card.classList.contains('expanded') ? 'true' : 'false');
  const openCard = event => {
    if (event.target.closest('.switch')) return;
    expandFeatureCard(card);
  };
  header.addEventListener('click', openCard);
  header.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      expandFeatureCard(card);
    }
  });
});


// Bokeh elements
let currentBlurRadius = 25.0;
const btnPreviewBokeh = document.getElementById('btnPreviewBokeh');
const bokehPreviewBox = document.getElementById('bokehPreviewBox');
const bokehPreviewImg = document.getElementById('bokehPreviewImg');
const bokehPresetsGrid = document.getElementById('bokehPresetsGrid');
const bokehSlider = document.getElementById('bokehSlider');
const bokehRadiusText = document.getElementById('bokehRadiusText');

if (bokehPresetsGrid) {
  bokehPresetsGrid.querySelectorAll('.preset-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      bokehPresetsGrid.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      currentBlurRadius = parseFloat(chip.dataset.blur || 25);
      if (bokehRadiusText) bokehRadiusText.innerText = currentBlurRadius + ' px';
      if (bokehSlider) bokehSlider.value = currentBlurRadius;
      if (typeof updatePipelineUI === 'function') updatePipelineUI();
    });
  });
}

if (bokehSlider) {
  bokehSlider.addEventListener('input', (e) => {
    currentBlurRadius = parseFloat(e.target.value);
    if (bokehRadiusText) bokehRadiusText.innerText = currentBlurRadius + ' px';
    if (bokehPresetsGrid) {
      bokehPresetsGrid.querySelectorAll('.preset-chip').forEach(chip => {
        if (parseFloat(chip.dataset.blur) === currentBlurRadius) chip.classList.add('active');
        else chip.classList.remove('active');
      });
    }
    if (typeof updatePipelineUI === 'function') updatePipelineUI();
  });
}

if (btnPreviewBokeh) {
  btnPreviewBokeh.addEventListener('click', () => {
    if (!currentTask || !currentTask.id) return;
    btnPreviewBokeh.innerText = '⏳ Đang xử lý...';
    btnPreviewBokeh.disabled = true;

    fetch('/api/preview-bokeh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: currentTask.id, blur_radius: currentBlurRadius })
    })
    .then(r => r.json())
    .then(data => {
      btnPreviewBokeh.innerText = '👁️ Xem trước 1 frame';
      btnPreviewBokeh.disabled = false;
      if (data.error) { showToast(data.error, '⚠️'); return; }
      if (data.preview_url && bokehPreviewBox && bokehPreviewImg) {
        bokehPreviewImg.src = data.preview_url;
        bokehPreviewBox.style.display = 'block';
        showToast('Đã tạo ảnh xem trước xóa phông!', '✨');
      }
    })
    .catch(err => {
      btnPreviewBokeh.innerText = '👁️ Xem trước 1 frame';
      btnPreviewBokeh.disabled = false;
      showToast('Lỗi xem trước: ' + err.message, '❌');
    });
  });
}


// Silence Metrics
const valSilenceCount = document.getElementById('valSilenceCount');
const valSavedTime = document.getElementById('valSavedTime');
const valNewDuration = document.getElementById('valNewDuration');
const timelineSpeechFill = document.getElementById('timelineSpeechFill');
const btnRescanSilence = document.getElementById('btnRescanSilence');

const valIntroTrim = document.getElementById('valIntroTrim');
const valOutroTrim = document.getElementById('valOutroTrim');

const manualStartInput = document.getElementById('manualStartInput');
const manualEndInput = document.getElementById('manualEndInput');

// Compression toggle & Target Size
const checkThenCompress = document.getElementById('checkThenCompress');
const targetSizeControls = document.getElementById('targetSizeControls');
const presetsGrid = document.getElementById('presetsGrid');
const sizeSlider = document.getElementById('sizeSlider');
const sliderValueText = document.getElementById('sliderValueText');
const targetBadge = document.getElementById('targetBadge');
const btnStartProcess = document.getElementById('btnStartProcess');
const btnProcessLabel = document.getElementById('btnProcessLabel');

// Progress & Results
const compressProgressPanel = document.getElementById('compressProgressPanel');
const compressStageText = document.getElementById('compressStageText');
const compressProgressFill = document.getElementById('compressProgressFill');
const compressPercentText = document.getElementById('compressPercentText');
const compressSpeedText = document.getElementById('compressSpeedText');
const compressEtaText = document.getElementById('compressEtaText');

const resultPanel = document.getElementById('resultPanel');
const resOrigMetrics = document.getElementById('resOrigMetrics');
const resCompMetrics = document.getElementById('resCompMetrics');
const resSavingsChip = document.getElementById('resSavingsChip');
const previewPlayer = document.getElementById('previewPlayer');
const btnDownload = document.getElementById('btnDownload');
const btnSaveDownloads = document.getElementById('btnSaveDownloads');
const btnNewTask = document.getElementById('btnNewTask');
const toast = document.getElementById('toast');

function showToast(msg, icon = '✅') {
  document.getElementById('toastMsg').innerText = msg;
  document.getElementById('toastIcon').innerText = icon;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

function formatDuration(sec) {
  if (!sec || isNaN(sec)) return '0:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

function parseSeconds(val) {
  if (typeof val === 'number') return val;
  val = val.trim();
  if (val.includes(':')) {
    const parts = val.split(':');
    return (parseFloat(parts[0]) * 60) + parseFloat(parts[1] || 0);
  }
  return parseFloat(val) || 0.0;
}

// Drag & Drop
['dragenter', 'dragover'].forEach(eventName => {
  dropzone.addEventListener(eventName, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(eventName => {
  dropzone.addEventListener(eventName, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('dragover');
  });
});

dropzone.addEventListener('drop', (e) => {
  const files = e.dataTransfer.files;
  if (files && files.length > 0) handleFileSelected(files[0]);
});

btnBrowse.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});
dropzone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) {
    handleFileSelected(e.target.files[0]);
  }
});

// Upload Video
function handleFileSelected(file) {
  if (!file) return;

  uploadProgressBox.style.display = 'block';
  uploadStatusText.innerText = `Đang tải "${file.name}" vào bộ xử lý...`;
  uploadProgressFill.style.width = '0%';
  uploadPercent.innerText = '0%';

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/upload', true);
  xhr.setRequestHeader('X-File-Name', encodeURIComponent(file.name));

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      uploadProgressFill.style.width = `${pct}%`;
      uploadPercent.innerText = `${pct}%`;
    }
  };

  xhr.onload = () => {
    if (xhr.status === 200) {
      const data = JSON.parse(xhr.responseText);
      currentTask = data;
      displayVideoInfo(data);
      // Tự động phân tích khoảng lặng ngay sau khi upload
      analyzeSilences();
    } else {
      showToast('Tải video thất bại!', '❌');
    }
    uploadProgressBox.style.display = 'none';
  };

  xhr.onerror = () => {
    showToast('Lỗi kết nối khi tải video', '❌');
    uploadProgressBox.style.display = 'none';
  };

  xhr.send(file);
}

function displayVideoInfo(task) {
  uploadSection.style.display = 'none';
  configSection.style.display = 'block';
  videoCard.style.display = 'block';
  setWorkflowStep('configure');

  videoFilename.innerText = task.filename;
  videoThumb.src = task.thumbnail_url || '';
  videoOrigSize.innerText = `${task.info.size_mb} MB`;
  videoDuration.innerText = formatDuration(task.info.duration);
  videoDimensions.innerText = task.info.width ? `${task.info.width}x${task.info.height}` : 'Tự động';

  if (task.info.has_audio) {
    audioTag.innerText = '🔊 Audio Stereo';
    audioTag.style.display = 'inline-flex';
  } else {
    audioTag.innerText = '🔇 Không có tiếng';
    audioTag.style.display = 'inline-flex';
  }

  manualStartInput.value = '0.0';
  manualEndInput.value = (task.info.duration || 60).toFixed(1);
  setTargetMb(18);
  updatePipelineUI();
}

// Phân tích khoảng im lặng
function analyzeSilences() {
  if (!currentTask) return;

  valSilenceCount.innerText = 'Đang quét...';
  valSavedTime.innerText = '...';
  valNewDuration.innerText = '...';

  fetch('/api/analyze-silence', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id: currentTask.id,
      noise_db: -30,
      min_silence: SMOOTH_PROFILES[currentSmoothProfile].min_silence,
      pad: SMOOTH_PROFILES[currentSmoothProfile].pad,
      merge_gap: SMOOTH_PROFILES[currentSmoothProfile].merge_gap
    })
  })
  .then(res => res.json())
  .then(data => {
    currentSilenceData = data;
    valSilenceCount.innerText = `${data.silence_count} đoạn`;
    valSavedTime.innerText = `-${data.total_silence}s (${data.saved_percent}%)`;
    valNewDuration.innerText = formatDuration(data.estimated_duration);

    valIntroTrim.innerText = `${data.intro_silence}s`;
    valOutroTrim.innerText = `${data.outro_silence}s`;

    const speechRatio = currentTask.info.duration > 0 ? (data.estimated_duration / currentTask.info.duration) * 100 : 100;
    timelineSpeechFill.style.width = `${Math.min(100, Math.max(5, speechRatio))}%`;
    updatePipelineUI();
  })
  .catch(err => {
    console.error(err);
    valSilenceCount.innerText = '0 đoạn';
    valSavedTime.innerText = '0s';
    valNewDuration.innerText = formatDuration(currentTask.info.duration);
    updatePipelineUI();
  });
}

btnRescanSilence.addEventListener('click', analyzeSilences);

// ==========================================
// STUDIO MODULAR PIPELINE EVENT LISTENERS
// ==========================================

// Module 1: Trim Toggle & Mode Selector
if (toggleTrim) {
  toggleTrim.addEventListener('change', () => {
    isTrimEnabled = toggleTrim.checked;
    cardTrim.classList.toggle('active', isTrimEnabled);
    cardTrim.classList.toggle('disabled', !isTrimEnabled);
    if (isTrimEnabled) expandFeatureCard(cardTrim);
    updatePipelineUI();
  });
}

trimPills.forEach(pill => {
  pill.addEventListener('click', () => {
    trimPills.forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    currentTrimMode = pill.dataset.trimMode;
    Object.entries(trimSubviews).forEach(([k, el]) => {
      if (el) el.classList.toggle('active', k === currentTrimMode);
    });
    updatePipelineUI();
  });
});

// Module 2: Bokeh Toggle
if (toggleBokeh) {
  toggleBokeh.addEventListener('change', () => {
    isBokehEnabled = toggleBokeh.checked;
    cardBokeh.classList.toggle('active', isBokehEnabled);
    cardBokeh.classList.toggle('disabled', !isBokehEnabled);
    if (isBokehEnabled) expandFeatureCard(cardBokeh);
    updatePipelineUI();
  });
}

// Module 3: Compress Toggle
if (toggleCompress) {
  toggleCompress.addEventListener('change', () => {
    isCompressEnabled = toggleCompress.checked;
    cardCompress.classList.toggle('active', isCompressEnabled);
    cardCompress.classList.toggle('disabled', !isCompressEnabled);
    if (isCompressEnabled) expandFeatureCard(cardCompress);
    updatePipelineUI();
  });
}

// Cập nhật quy trình trực quan (Pipeline Indicator) & Tiêu đề nút bấm
function updatePipelineUI() {
  const activeCount = (isTrimEnabled ? 1 : 0) + (isBokehEnabled ? 1 : 0) + (isCompressEnabled ? 1 : 0);
  if (activeFeaturesCountBadge) {
    activeFeaturesCountBadge.innerText = `${activeCount}/3 tính năng đang bật`;
  }

  // Tạo các bước trong Pipeline Indicator
  const steps = [];
  if (isTrimEnabled) {
    let trimLabel = 'Lọc khoảng lặng';
    if (currentSilenceData && currentSilenceData.total_silence > 0 && currentTrimMode === 'auto_silence') {
      trimLabel = `Lọc khoảng lặng (-${currentSilenceData.total_silence}s)`;
    } else if (currentTrimMode === 'intro_outro') {
      trimLabel = 'Cắt đầu & đuôi';
    } else if (currentTrimMode === 'manual') {
      trimLabel = 'Cắt mốc thủ công';
    }
    steps.push({ icon: '✂️', label: trimLabel, cssClass: 'step-trim' });
  }

  if (isBokehEnabled) {
    steps.push({ icon: '🎭', label: `Xóa phông AI (${currentBlurRadius}px)`, cssClass: 'step-bokeh' });
  }

  if (isCompressEnabled) {
    steps.push({ icon: '⚡', label: `Nén Video (< ${targetMb} MB)`, cssClass: 'step-compress' });
  } else {
    steps.push({ icon: '✨', label: 'Xuất chất lượng gốc 100%', cssClass: 'step-compress' });
  }

  if (pipelineFlowSteps) {
    if (!isTrimEnabled && !isBokehEnabled && !isCompressEnabled) {
      pipelineFlowSteps.innerHTML = '<span style="color: #f43f5e; font-size: 0.85rem; font-weight: 600;">⚠️ Chưa chọn tính năng nào! Hãy bật ít nhất 1 tính năng phía trên để xử lý.</span>';
      btnStartProcess.disabled = true;
      btnProcessLabel.innerText = '⚠️ Vui lòng bật ít nhất 1 tính năng';
      return;
    }

    pipelineFlowSteps.innerHTML = steps.map((s, idx) => {
      const chip = `<div class="pipeline-step-chip ${s.cssClass}">${s.icon} ${s.label}</div>`;
      if (idx < steps.length - 1) {
        return chip + '<span class="pipeline-step-arrow">➔</span>';
      }
      return chip;
    }).join('');
  }

  // Cập nhật nhãn nút bấm hành động
  btnStartProcess.disabled = false;
  const actions = [];
  if (isTrimEnabled) {
    if (currentTrimMode === 'auto_silence') actions.push('Lọc Khoảng Lặng');
    else if (currentTrimMode === 'intro_outro') actions.push('Cắt Đầu Đuôi');
    else actions.push('Cắt Thủ Công');
  }
  if (isBokehEnabled) actions.push('Xóa Phông AI');
  if (isCompressEnabled) actions.push(`Nén < ${targetMb}MB`);
  else actions.push('Chất Lượng Gốc');

  btnProcessLabel.innerText = '🚀 Bắt Đầu: ' + actions.join(' + ');
}

// Preset and Slider
presetsGrid.querySelectorAll('.preset-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    setTargetMb(parseFloat(chip.dataset.mb));
  });
});

sizeSlider.addEventListener('input', (e) => {
  setTargetMb(parseFloat(e.target.value), false);
});

function setTargetMb(mb, updateSlider = true) {
  targetMb = mb;
  targetBadge.innerText = `${mb.toFixed(1)} MB`;
  sliderValueText.innerText = `${mb} MB`;
  if (updateSlider) sizeSlider.value = mb;

  presetsGrid.querySelectorAll('.preset-chip').forEach(chip => {
    if (parseFloat(chip.dataset.mb) === mb) chip.classList.add('active');
    else chip.classList.remove('active');
  });

  updatePipelineUI();
}

// Reset
btnRemoveFile.addEventListener('click', resetToUpload);
function resetToUpload() {
  if (currentTask) fetch('/api/selection', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ previous_id: currentTask.id })
  });
  document.getElementById('aiStageNotice').hidden = true;
  currentTask = null;
  fileInput.value = '';
  configSection.style.display = 'none';
  compressProgressPanel.style.display = 'none';
  resultPanel.style.display = 'none';
  uploadSection.style.display = 'block';
  setWorkflowStep('upload');
  previewPlayer.pause();
  previewPlayer.removeAttribute('src');
  previewPlayer.load();
  reviewPlayer.pause();
  reviewPlayer.removeAttribute('src');
  reviewPlayer.load();
  if (progressPollTimer) clearInterval(progressPollTimer);
  progressPollTimer = null;
}

// Start Processing
btnStartProcess.addEventListener('click', () => {
  if (!currentTask || !currentTask.id) return;
  if (!isTrimEnabled && !isBokehEnabled && !isCompressEnabled) {
    showToast('Vui lòng bật ít nhất 1 tính năng!', '⚠️');
    return;
  }

  previewPlayer.pause();
  previewPlayer.removeAttribute('src');
  previewPlayer.load();
  btnStartProcess.disabled = true;
  configSection.style.display = 'none';
  compressProgressPanel.style.display = 'block';
  setWorkflowStep('export');
  compressProgressFill.style.width = '0%';
  compressPercentText.innerText = '0%';
  compressStageText.innerText = 'Đang chuẩn bị xuất an toàn, mỗi lần một video…';

  const payload = {
    id: currentTask.id,
    hardware_encode: document.getElementById("toggleHardwareEncode").checked,
    mode: isTrimEnabled ? currentTrimMode : 'none',
    enable_bokeh: isBokehEnabled,
    blur_radius: currentBlurRadius,
    then_compress: isCompressEnabled,
    target_mb: targetMb,
    start_time: parseSeconds(manualStartInput.value),
    end_time: parseSeconds(manualEndInput.value),
    noise_db: -30,
    min_silence: SMOOTH_PROFILES[currentSmoothProfile].min_silence,
    pad: SMOOTH_PROFILES[currentSmoothProfile].pad,
    merge_gap: SMOOTH_PROFILES[currentSmoothProfile].merge_gap
  };

  fetch('/api/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      startProgressPolling(currentTask.id);
    } else {
      showToast('Lỗi: ' + (data.error || ''), '❌');
      btnStartProcess.disabled = false;
      configSection.style.display = 'block';
      compressProgressPanel.style.display = 'none';
      setWorkflowStep('configure');
    }
  })
  .catch(err => {
    showToast('Lỗi kết nối: ' + err.message, '❌');
    btnStartProcess.disabled = false;
    configSection.style.display = 'block';
    compressProgressPanel.style.display = 'none';
    setWorkflowStep('configure');
  });
});

function startProgressPolling(taskId) {
  if (progressPollTimer) clearInterval(progressPollTimer);
  progressPollTimer = null;

  progressPollTimer = setInterval(() => {
    fetch(`/api/progress?id=${taskId}`)
      .then(res => res.json())
      .then(data => {
        if (!currentTask || currentTask.id !== taskId) return;
        if (data.error) {
          clearInterval(progressPollTimer); progressPollTimer = null;
          showToast('Lỗi: ' + data.error, '❌');
          resetToUpload();
          return;
        }

        const pct = data.progress || 0;
        compressProgressFill.style.width = `${pct}%`;
        compressPercentText.innerText = `${pct}%`;

        if (data.stage) compressStageText.innerText = data.stage;
        if (data.speed) compressSpeedText.innerText = data.speed;

        if (data.status === 'completed') {
          clearInterval(progressPollTimer); progressPollTimer = null;
          handleProcessCompleted(data);
        } else if (data.status === 'error') {
          clearInterval(progressPollTimer); progressPollTimer = null;
          showToast('Lỗi xử lý video: ' + (data.error || 'Thất bại'), '❌');
          resetToUpload();
        }
      })
      .catch(console.error);
  }, 400);
}

function handleProcessCompleted(data) {
  compressProgressPanel.style.display = 'none';
  resultPanel.style.display = 'block';
  btnStartProcess.disabled = false;

  const result = data.result;
  const origDur = formatDuration(currentTask.info.duration);
  const newDur = formatDuration(result.duration);

  resOrigMetrics.innerHTML = `${currentTask.info.size_mb} MB <span style="font-size: 1rem; color: var(--text-dim);">(${origDur})</span>`;
  resCompMetrics.innerHTML = `${result.output_size_mb} MB <span style="font-size: 1rem; color: #34d399;">(${newDur})</span>`;

  if (result.saved_time_sec > 0) {
    resSavingsChip.innerText = `Cắt -${result.saved_time_sec}s | Giảm ${result.saved_percent}% MB`;
  } else {
    resSavingsChip.innerText = `Giảm ${result.saved_percent}%`;
  }

  btnDownload.href = `/api/download?id=${currentTask.id}`;
  btnDownload.setAttribute('download', result.output_filename);
  previewPlayer.src = `/api/preview?id=${currentTask.id}`;

  showToast('Xử lý video hoàn tất thành công!', '🎉');
}

// Lưu Downloads
btnSaveDownloads.addEventListener('click', () => {
  if (!currentTask || !currentTask.id) return;
  btnSaveDownloads.disabled = true;
  btnSaveDownloads.innerText = 'Đang lưu vào Downloads...';

  fetch('/api/save-downloads', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: currentTask.id })
  })
  .then(res => res.json())
  .then(data => {
    btnSaveDownloads.disabled = false;
    btnSaveDownloads.innerHTML = '📂 Lưu vào Downloads & Mở Finder';
    if (data.success) {
      showToast('Đã lưu vào Downloads và mở Finder!', '📁');
    } else {
      showToast('Lỗi lưu file: ' + (data.error || ''), '❌');
    }
  })
  .catch(err => {
    btnSaveDownloads.disabled = false;
    btnSaveDownloads.innerHTML = '📂 Lưu vào Downloads & Mở Finder';
    showToast('Lỗi: ' + err.message, '❌');
  });
});

btnNewTask.addEventListener('click', resetToUpload);

// Observe jobs started by Codex without starting duplicate workers.
let mcpObserverBusy = false;
let lastMcpJob = null;
setInterval(async () => {
  if (!currentTask || progressPollTimer || mcpObserverBusy) return;
  mcpObserverBusy = true;
  const id = currentTask.id;
  try {
    const r = await fetch(`/api/progress?id=${id}`);
    const data = await r.json();
    if (!currentTask || currentTask.id !== id) return;
    const notice = document.getElementById('aiStageNotice');
    notice.textContent = data.ai_stage || '';
    notice.hidden = !data.ai_stage;
    if (data.status === 'processing') {
      previewPlayer.pause();
      previewPlayer.removeAttribute('src');
      previewPlayer.load();
      lastMcpJob = data.mcp_job_id;
      configSection.style.display = 'none';
      resultPanel.style.display = 'none';
      compressProgressPanel.style.display = 'block';
      setWorkflowStep('export');
      startProgressPolling(id);
    } else if (data.status === 'completed' && data.result && data.mcp_job_id &&
               lastMcpJob !== data.mcp_job_id) {
      lastMcpJob = data.mcp_job_id;
      startProgressPolling(id);
    }
  } catch (_) { /* The app may be shutting down. */ }
  finally { mcpObserverBusy = false; }
}, 1500);

// Provider/model settings: secrets never enter localStorage or GET URLs.
const aiUI = Object.fromEntries(['aiProfileSelect', 'aiProvider', 'aiProfileName', 'aiBaseUrl', 'aiModelId', 'aiApiKey', 'aiRememberKey', 'aiModelOptions', 'cloudAIStatus', 'btnCloudAI'].map(id => [id, document.getElementById(id)]));
let aiConfig = { profiles: [], presets: {} };
let editingAIProfile = null;
let cloudRunActive = false;
async function aiRequest(action, data = {}) {
  const response = await fetch(`/api/ai/${action}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'AI gặp lỗi.');
  return value;
}
function showAIConfig(config) {
  aiConfig = config;
  aiUI.aiProfileSelect.replaceChildren(new Option('Chọn model AI…', ''));
  config.profiles.forEach(p => aiUI.aiProfileSelect.add(new Option(`${p.name} · ${p.model}${p.has_key ? '' : ' (cần key)'}`, p.id)));
  aiUI.aiProfileSelect.value = config.selected_id || '';
}
function editAIProfile(id) {
  const p = aiConfig.profiles.find(p => p.id === id);
  editingAIProfile = p ? p.id : null;
  aiUI.aiProfileName.value = p ? p.name : '';
  aiUI.aiModelId.value = p ? p.model : '';
  aiUI.aiBaseUrl.value = p ? p.base_url : aiConfig.presets.OpenAI || 'https://api.openai.com/v1';
  aiUI.aiProvider.value = Object.keys(aiConfig.presets).find(k => aiConfig.presets[k] === aiUI.aiBaseUrl.value) || 'Tùy chỉnh';
  aiUI.aiApiKey.value = '';
  aiUI.aiRememberKey.checked = !!(p && p.key_saved);
  aiUI.aiModelOptions.replaceChildren();
}
function aiAction(buttonId, handler) {
  document.getElementById(buttonId).addEventListener('click', async event => {
    const button = event.currentTarget;
    button.disabled = true;
    try { await handler(); } catch (e) { aiUI.cloudAIStatus.textContent = e.message; }
    finally { button.disabled = false; }
  });
}
aiUI.aiProvider.addEventListener('change', () => {
  if (aiConfig.presets[aiUI.aiProvider.value]) aiUI.aiBaseUrl.value = aiConfig.presets[aiUI.aiProvider.value];
  // A different provider is always saved as a new credential scope.
  editingAIProfile = null;
  aiUI.aiApiKey.value = '';
  aiUI.aiModelOptions.replaceChildren();
});
aiUI.aiProfileSelect.addEventListener('change', async () => {
  try {
    if (aiUI.aiProfileSelect.value) showAIConfig(await aiRequest('select', { id: aiUI.aiProfileSelect.value }));
    editAIProfile(aiUI.aiProfileSelect.value);
  } catch (e) { aiUI.cloudAIStatus.textContent = e.message; }
});
aiAction('aiNewProfile', async () => { editAIProfile(null); aiUI.cloudAIStatus.textContent = 'Nhập model mới rồi lưu. Cấu hình hiện tại được giữ nguyên.'; });
aiAction('aiSaveProfile', async () => {
  const config = await aiRequest('save', { id: editingAIProfile, name: aiUI.aiProfileName.value, model: aiUI.aiModelId.value, base_url: aiUI.aiBaseUrl.value, api_key: aiUI.aiApiKey.value, remember_key: aiUI.aiRememberKey.checked });
  aiUI.aiApiKey.value = '';
  showAIConfig(config); editAIProfile(config.selected_id);
  aiUI.cloudAIStatus.textContent = 'Đã lưu model. Có thể thêm cấu hình khác hoặc bắt đầu tối ưu.';
});
aiAction('aiLoadModels', async () => {
  if (!editingAIProfile && !aiUI.aiApiKey.value) throw new Error('Nhập API key để tải các model hiện có.');
  aiUI.cloudAIStatus.textContent = 'Đang tải danh sách model từ nhà cung cấp…';
  const result = await aiRequest('models', { id: editingAIProfile, base_url: aiUI.aiBaseUrl.value, api_key: aiUI.aiApiKey.value });
  aiUI.aiModelOptions.replaceChildren(...result.models.map(id => new Option(id, id)));
  aiUI.cloudAIStatus.textContent = `Đã tải ${result.models.length} model. Chọn model hỗ trợ chat trong ô Model ID rồi lưu.`;
});
aiAction('aiDeleteProfile', async () => {
  if (!editingAIProfile) return;
  const config = await aiRequest('delete', { id: editingAIProfile });
  showAIConfig(config); editAIProfile(config.selected_id);
  aiUI.cloudAIStatus.textContent = 'Đã xóa cấu hình và khóa được ghi nhớ.';
});
let cloudReviewJob = null;
let reviewStopAt = null;
const reviewPlayer = document.getElementById('aiReviewPlayer');
reviewPlayer.addEventListener('timeupdate', () => {
  if (reviewStopAt !== null && reviewPlayer.currentTime >= reviewStopAt) {
    reviewPlayer.pause(); reviewStopAt = null;
  }
});
function playReviewRange(range) {
  const seek = () => {
    reviewPlayer.currentTime = Math.max(0, range[0] - .3);
    reviewStopAt = range[1] + .3;
    reviewPlayer.play().catch(() => {});
  };
  if (reviewPlayer.readyState) seek();
  else reviewPlayer.addEventListener('loadedmetadata', seek, {once:true});
}
function rangeButton(range, label) {
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'btn-secondary';
  button.textContent = `${label} ${range[0].toFixed(2)}–${range[1].toFixed(2)}s`;
  button.addEventListener('click', () => playReviewRange(range));
  return button;
}
function showCloudReview(jobId, state) {
  cloudReviewJob = jobId;
  btnStartProcess.disabled = true;
  document.getElementById('aiReviewPanel').hidden = false;
  const summary = state.review ? state.review.summary : '';
  document.getElementById('aiReviewSummary').textContent = `${state.model} · ${summary} Nguồn: ${(state.source_duration || 0).toFixed(1)}s. Bản nháp sau lọc khoảng lặng: ${(state.draft_duration || 0).toFixed(1)}s.`;
  const rows = document.getElementById('aiReviewRows'); rows.replaceChildren();
  if (!state.review_rows.length) {
    const p = document.createElement('p'); p.textContent = 'Không có câu được AI đề xuất bỏ. Nếu duyệt, chỉ áp dụng phần cắt khoảng lặng sơ bộ.'; rows.append(p);
  }
  state.review_rows.forEach(row => {
    const card = document.createElement('div'); card.className = 'ai-review-card';
    const label = document.createElement('label');
    const check = document.createElement('input'); check.type = 'checkbox'; check.checked = true; check.dataset.decisionIndex = row.index;
    label.append(check, document.createTextNode(` Bỏ: ${row.removed_text}`)); card.append(label);
    if (row.replacement_text) { const kept = document.createElement('p'); kept.textContent = 'Giữ thay thế: ' + row.replacement_text; card.append(kept); }
    const reason = document.createElement('p'); reason.className = 'ai-settings-note'; reason.textContent = row.reason; card.append(reason);
    const buttons = document.createElement('div'); buttons.className = 'ai-settings-actions';
    row.source_ranges.forEach(range => buttons.append(rangeButton(range, 'Nghe/xem đoạn'))); card.append(buttons); rows.append(card);
  });
  const silenceRows = document.getElementById('aiSilenceReview'); silenceRows.replaceChildren();
  (state.preliminary_cuts || []).forEach(range => silenceRows.append(rangeButton(range, 'Khoảng lặng')));
  if (!state.preliminary_cuts || !state.preliminary_cuts.length) silenceRows.textContent = 'Không có khoảng lặng được đề xuất cắt.';
  reviewPlayer.src = `/api/review-source?job_id=${encodeURIComponent(jobId)}`;
  aiUI.btnCloudAI.disabled = true;
}
function hideCloudReview() {
  cloudReviewJob = null;
  btnStartProcess.disabled = false;
  document.getElementById('aiReviewPanel').hidden = true;
  reviewPlayer.pause(); reviewPlayer.removeAttribute('src'); reviewPlayer.load();
}
async function pollCloudJob(jobId, videoId) {
  while (true) {
    const state = await aiRequest('job', {job_id:jobId});
    aiUI.cloudAIStatus.textContent = state.stage || 'Đang xử lý AI…';
    if (state.status === 'awaiting_review') { showCloudReview(jobId, state); return; }
    if (state.status === 'error') throw new Error(state.error || 'AI chưa hoàn tất.');
    if (state.status === 'cancelled') { hideCloudReview(); return; }
    if (state.status === 'completed') {
      aiUI.cloudAIStatus.textContent = `Đã xuất với ${state.model}.`;
      if (currentTask && currentTask.id === videoId) startProgressPolling(videoId);
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 1200));
  }
}
aiUI.btnCloudAI.addEventListener('click', async () => {
  if (cloudRunActive || cloudReviewJob) return;
  if (!currentTask) { showToast('Chọn video trước khi chạy AI.', '⚠️'); return; }
  if (!aiUI.aiProfileSelect.value) { document.getElementById('aiSettings').open = true; aiUI.cloudAIStatus.textContent = 'Thêm và chọn model AI trước.'; return; }
  cloudRunActive = true; aiUI.btnCloudAI.disabled = true;
  const videoId = currentTask.id;
  try {
    const job = await aiRequest('start', { profile_id: aiUI.aiProfileSelect.value, request_id: crypto.randomUUID(), target_mb: targetMb, then_compress: isCompressEnabled, hardware_encode: document.getElementById("toggleHardwareEncode").checked });
    await pollCloudJob(job.job_id, videoId);
  } catch (e) { aiUI.cloudAIStatus.textContent = e.message; }
  finally { cloudRunActive = false; aiUI.btnCloudAI.disabled = !!cloudReviewJob; }
});
aiAction('aiApproveReview', async () => {
  if (!cloudReviewJob) return;
  const id = cloudReviewJob;
  const indexes = Array.from(document.querySelectorAll('#aiReviewRows input:checked')).map(input => Number(input.dataset.decisionIndex));
  await aiRequest('approve', {job_id:id, decision_indexes:indexes, hardware_encode:document.getElementById('toggleHardwareEncode').checked});
  hideCloudReview(); btnStartProcess.disabled = true; cloudRunActive = true; aiUI.btnCloudAI.disabled = true;
  try { await pollCloudJob(id, currentTask && currentTask.id); }
  finally { cloudRunActive = false; aiUI.btnCloudAI.disabled = !!cloudReviewJob; }
});
aiAction('aiCancelReview', async () => {
  if (!cloudReviewJob) return;
  await aiRequest('cancel', {job_id:cloudReviewJob});
  hideCloudReview(); aiUI.btnCloudAI.disabled = false;
  aiUI.cloudAIStatus.textContent = 'Đã hủy đề xuất. Chưa xuất hay ghép video.';
});
aiRequest('settings').then(async config => {
  showAIConfig(config); editAIProfile(config.selected_id);
  if (config.selected_video && config.selected_video.video_id && !currentTask) {
    const v = config.selected_video;
    currentTask = {id:v.video_id, filename:v.filename, info:v.info, thumbnail_url:`/api/thumbnail?id=${v.video_id}`};
    displayVideoInfo(currentTask);
  }
  const active = config.active_jobs && config.active_jobs[0];
  if (active) {
    cloudRunActive = true; aiUI.btnCloudAI.disabled = true;
    try { await pollCloudJob(active.job_id, currentTask && currentTask.id); }
    finally { cloudRunActive = false; aiUI.btnCloudAI.disabled = !!cloudReviewJob; }
  }
}).catch(e => { aiUI.cloudAIStatus.textContent = e.message; });
