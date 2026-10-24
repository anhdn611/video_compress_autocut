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
    updatePipelineUI();
  });
}

// Module 3: Compress Toggle
if (toggleCompress) {
  toggleCompress.addEventListener('change', () => {
    isCompressEnabled = toggleCompress.checked;
    cardCompress.classList.toggle('active', isCompressEnabled);
    cardCompress.classList.toggle('disabled', !isCompressEnabled);
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
  currentTask = null;
  fileInput.value = '';
  configSection.style.display = 'none';
  compressProgressPanel.style.display = 'none';
  resultPanel.style.display = 'none';
  uploadSection.style.display = 'block';
  previewPlayer.pause();
  previewPlayer.src = '';
  if (progressPollTimer) clearInterval(progressPollTimer);
}

// Start Processing
btnStartProcess.addEventListener('click', () => {
  if (!currentTask || !currentTask.id) return;
  if (!isTrimEnabled && !isBokehEnabled && !isCompressEnabled) {
    showToast('Vui lòng bật ít nhất 1 tính năng!', '⚠️');
    return;
  }

  btnStartProcess.disabled = true;
  configSection.style.display = 'none';
  compressProgressPanel.style.display = 'block';
  compressProgressFill.style.width = '0%';
  compressPercentText.innerText = '0%';
  compressStageText.innerText = 'Đang khởi động phần cứng Apple Silicon...';

  const payload = {
    id: currentTask.id,
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
    }
  })
  .catch(err => {
    showToast('Lỗi kết nối: ' + err.message, '❌');
    btnStartProcess.disabled = false;
    configSection.style.display = 'block';
    compressProgressPanel.style.display = 'none';
  });
});

function startProgressPolling(taskId) {
  if (progressPollTimer) clearInterval(progressPollTimer);

  progressPollTimer = setInterval(() => {
    fetch(`/api/progress?id=${taskId}`)
      .then(res => res.json())
      .then(data => {
        if (data.error) {
          clearInterval(progressPollTimer);
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
          clearInterval(progressPollTimer);
          handleProcessCompleted(data);
        } else if (data.status === 'error') {
          clearInterval(progressPollTimer);
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
