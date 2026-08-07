document.addEventListener("DOMContentLoaded", async () => {
  // Register Service Worker for PWA (Android App)
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(err => console.log('SW reg error:', err));
  }

  // DOM Elements
  const engineBtns = document.querySelectorAll(".engine-btn");
  const apiKeyInput = document.getElementById("api-key-input");
  const fileInput = document.getElementById("file-input");
  const cameraInput = document.getElementById("camera-input");
  const dropZone = document.getElementById("drop-zone");
  const samplesGrid = document.getElementById("samples-grid");
  const btnExtract = document.getElementById("btn-extract");
  const btnVCard = document.getElementById("btn-vcard");
  const btnExportCsv = document.getElementById("btn-export-csv");
  const btnCameraMobile = document.getElementById("btn-camera-mobile");
  
  const canvasElement = document.getElementById("card-canvas");
  const cropper = new CanvasCropper(canvasElement);

  // Form Fields
  const inputCompany = document.getElementById("field-company");
  const inputName = document.getElementById("field-name");
  const inputTitle = document.getElementById("field-title");
  const inputPhone = document.getElementById("field-phone");
  const inputPhone2 = document.getElementById("field-phone2");
  const inputEmail = document.getElementById("field-email");
  const inputWebsite = document.getElementById("field-website");
  const inputAddress = document.getElementById("field-address");

  const singleResultPanel = document.getElementById("single-result-panel");
  const compareResultPanel = document.getElementById("compare-result-panel");

  // State Variables
  let selectedEngine = "v1";
  let selectedFile = null;
  let selectedSampleName = null;
  let currentCardData = {};
  let scannedCardsHistory = [];

  // Cache for last extraction results per engine mode
  let lastExtractionCache = {
    v1: null,
    v2: null,
    compare: null
  };

  const btnReset = document.getElementById("btn-reset");
  const btnResetHeader = document.getElementById("btn-reset-header");

  const clearForm = () => {
    inputCompany.value = "";
    inputName.value = "";
    inputTitle.value = "";
    inputPhone.value = "";
    if (inputPhone2) inputPhone2.value = "";
    inputEmail.value = "";
    inputWebsite.value = "";
    inputAddress.value = "";
    currentCardData = {};
  };

  const resetAllCacheAndForm = () => {
    clearForm();
    lastExtractionCache = { v1: null, v2: null, compare: null };
    scannedCardsHistory = [];

    ["v1", "v2"].forEach(prefix => {
      const setText = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
      };
      setText(`${prefix}-company`, "(Không tìm thấy)");
      setText(`${prefix}-name`, "(Không tìm thấy)");
      setText(`${prefix}-title`, "(Không tìm thấy)");
      setText(`${prefix}-phone`, "(Không tìm thấy)");
      setText(`${prefix}-phone2`, "(Không có SĐT 2)");
      setText(`${prefix}-email`, "(Không tìm thấy)");
      setText(`${prefix}-website`, "(Không tìm thấy)");
      setText(`${prefix}-latency`, "0 ms");
    });
  };

  if (btnReset) {
    btnReset.addEventListener("click", () => {
      resetAllCacheAndForm();
      const origText = btnReset.innerText;
      btnReset.innerText = "✓ Cleared!";
      setTimeout(() => btnReset.innerText = origText, 1500);
    });
  }

  if (btnResetHeader) {
    btnResetHeader.addEventListener("click", () => {
      resetAllCacheAndForm();
      const origText = btnResetHeader.innerText;
      btnResetHeader.innerText = "✓ Cleared!";
      setTimeout(() => btnResetHeader.innerText = origText, 1500);
    });
  }

  const formatPhone = (val) => (val || "").replace(/\./g, "").trim();

  const renderSingleResult = (data) => {
    if (!data) return;
    if (data.error) {
      alert(data.error);
    }

    inputCompany.value = data.company_name || "";
    inputName.value = data.full_name || "";
    inputTitle.value = data.job_title || "";
    inputPhone.value = formatPhone(data.phone);
    if (inputPhone2) inputPhone2.value = formatPhone(data.phone_2);
    inputEmail.value = data.email || "";
    inputWebsite.value = data.website || "";
    inputAddress.value = data.address || "";

    currentCardData = {
      company_name: inputCompany.value,
      full_name: inputName.value,
      job_title: inputTitle.value,
      phone: inputPhone.value,
      phone_2: inputPhone2 ? inputPhone2.value : "",
      email: inputEmail.value,
      website: inputWebsite.value,
      address: inputAddress.value
    };

    if (currentCardData.full_name || currentCardData.company_name) {
      scannedCardsHistory.push(currentCardData);
    }
  };

  const renderCompareResults = (v1Data, v2Data) => {
    const renderCard = (d, idPrefix) => {
      if (!d) return;
      const setText = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val || "";
      };

      setText(`${idPrefix}-engine`, d.engine);
      setText(`${idPrefix}-latency`, d.latency_ms ? `${d.latency_ms} ms` : "0 ms");
      setText(`${idPrefix}-company`, d.company_name || "(Không tìm thấy)");
      setText(`${idPrefix}-name`, d.full_name || "(Không tìm thấy)");
      setText(`${idPrefix}-title`, d.job_title || "(Không tìm thấy)");
      setText(`${idPrefix}-phone`, formatPhone(d.phone) || "(Không tìm thấy)");
      setText(`${idPrefix}-phone2`, formatPhone(d.phone_2) || "(Không có SĐT 2)");
      setText(`${idPrefix}-email`, d.email || "(Không tìm thấy)");
      setText(`${idPrefix}-website`, d.website || "(Không tìm thấy)");
      
      if (d.error) {
        setText(`${idPrefix}-company`, `[LỖI]: ${d.error}`);
      }
    };

    renderCard(v1Data, "v1");
    renderCard(v2Data, "v2");

    // Also populate single form with V1 or V2 by default
    if (v1Data && !v1Data.error) {
      renderSingleResult(v1Data);
    } else if (v2Data && !v2Data.error) {
      renderSingleResult(v2Data);
    }
  };

  // Engine Switch Handler
  engineBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      engineBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      selectedEngine = btn.dataset.engine;

      if (selectedEngine === "compare") {
        singleResultPanel.style.display = "none";
        compareResultPanel.style.display = "grid";
        if (lastExtractionCache.compare) {
          renderCompareResults(lastExtractionCache.compare.v1, lastExtractionCache.compare.v2);
        }
      } else {
        singleResultPanel.style.display = "block";
        compareResultPanel.style.display = "none";
        if (lastExtractionCache[selectedEngine]) {
          renderSingleResult(lastExtractionCache[selectedEngine]);
        } else if (selectedEngine === "v1" && lastExtractionCache.compare && lastExtractionCache.compare.v1) {
          renderSingleResult(lastExtractionCache.compare.v1);
        } else if (selectedEngine === "v2" && lastExtractionCache.compare && lastExtractionCache.compare.v2) {
          renderSingleResult(lastExtractionCache.compare.v2);
        }
      }
    });
  });

  // Load Sample Cards
  const loadSamples = async () => {
    const data = await ApiClient.getSampleCards();
    samplesGrid.innerHTML = "";
    if (!data.samples || data.samples.length === 0) {
      samplesGrid.innerHTML = `<span style="grid-column: span 4; color: var(--text-muted); font-size: 0.8rem;">Không tìm thấy ảnh mẫu</span>`;
      return;
    }

    data.samples.forEach((filename, idx) => {
      const sampleUrl = `/api/sample-cards/${filename}`;
      const thumb = document.createElement("div");
      thumb.className = `sample-thumb ${idx === 0 ? 'selected' : ''}`;
      thumb.innerHTML = `<img src="${sampleUrl}" alt="${filename}"><span style="position: absolute; bottom: 2px; right: 4px; font-size: 0.65rem; background: rgba(0,0,0,0.7); padding: 1px 4px; border-radius: 4px;">${filename}</span>`;
      
      thumb.addEventListener("click", () => {
        document.querySelectorAll(".sample-thumb").forEach(t => t.classList.remove("selected"));
        thumb.classList.add("selected");
        selectedFile = null;
        selectedSampleName = filename;
        lastExtractionCache = { v1: null, v2: null, compare: null };
        clearForm();
        cropper.loadImage(sampleUrl);
      });

      samplesGrid.appendChild(thumb);
    });

    // Load first sample by default
    if (data.samples.length > 0) {
      const firstUrl = `/api/sample-cards/${data.samples[0]}`;
      selectedSampleName = data.samples[0];
      cropper.loadImage(firstUrl);
    }
  };

  await loadSamples();

  // Drag & Drop & File Upload Handlers
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  if (btnCameraMobile) {
    btnCameraMobile.addEventListener("click", () => cameraInput.click());
  }

  if (cameraInput) {
    cameraInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFileSelected(e.target.files[0]);
      }
    });
  }

  const handleFileSelected = (file) => {
    selectedFile = file;
    selectedSampleName = null;
    lastExtractionCache = { v1: null, v2: null, compare: null };
    clearForm();
    document.querySelectorAll(".sample-thumb").forEach(t => t.classList.remove("selected"));

    const reader = new FileReader();
    reader.onload = (e) => {
      cropper.loadImage(e.target.result);
    };
    reader.readAsDataURL(file);
  };

  // Copy to Clipboard Handlers
  document.querySelectorAll(".btn-copy").forEach(btn => {
    btn.addEventListener("click", () => {
      const fieldId = btn.dataset.for;
      const inputEl = document.getElementById(fieldId);
      if (inputEl && inputEl.value) {
        navigator.clipboard.writeText(inputEl.value);
        const origText = btn.innerText;
        btn.innerText = "✓ Copied";
        setTimeout(() => btn.innerText = origText, 1500);
      }
    });
  });

  // Core Extract Trigger Handler
  btnExtract.addEventListener("click", async () => {
    btnExtract.disabled = true;
    btnExtract.innerHTML = `<span class="spinner"></span> Đang trích xuất...`;

    const cropPoints = cropper.getOriginalPoints();
    const apiKey = apiKeyInput ? apiKeyInput.value.trim() : null;

    try {
      const res = await ApiClient.extractCardInfo({
        file: selectedFile,
        sampleFilename: selectedSampleName,
        engine: selectedEngine,
        apiKey: apiKey,
        cropPoints: cropPoints
      });

      if (selectedEngine === "compare") {
        lastExtractionCache.compare = res;
        if (res.v1) lastExtractionCache.v1 = res.v1;
        if (res.v2) lastExtractionCache.v2 = res.v2;
        renderCompareResults(res.v1, res.v2);
      } else {
        lastExtractionCache[selectedEngine] = res.result;
        renderSingleResult(res.result);
      }
    } catch (e) {
      alert("Lỗi trích xuất: " + e.message);
    } finally {
      btnExtract.disabled = false;
      btnExtract.innerHTML = `✨ Trích Xuất Dữ Liệu`;
    }
  });

  // Export Button Handlers
  const DEFAULT_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwgQ-rlckIiiYRh4xe9jsnEYwtsoP006RVIrnJsOQge9EftfTnzLikt5KoTyZnJmlv2ZQ/exec";
  const btnSyncGsheet = document.getElementById("btn-sync-gsheet");

  if (btnVCard) {
    btnVCard.addEventListener("click", () => {
      const cardToExport = {
        company_name: inputCompany.value,
        full_name: inputName.value,
        job_title: inputTitle.value,
        phone: inputPhone.value,
        phone_2: inputPhone2 ? inputPhone2.value : "",
        email: inputEmail.value,
        website: inputWebsite.value,
        address: inputAddress.value
      };
      if (!cardToExport.full_name && !cardToExport.company_name) {
        alert("Vui lòng thực hiện trích xuất thông tin card trước khi tải vCard.");
        return;
      }
      ApiClient.downloadVCard(cardToExport);
    });
  }

  const getCardsToExport = () => {
    if (scannedCardsHistory.length === 0) {
      const cardToExport = {
        company_name: inputCompany.value,
        full_name: inputName.value,
        job_title: inputTitle.value,
        phone: inputPhone.value,
        phone_2: inputPhone2 ? inputPhone2.value : "",
        email: inputEmail.value,
        website: inputWebsite.value,
        address: inputAddress.value
      };
      if (cardToExport.full_name || cardToExport.company_name) {
        scannedCardsHistory.push(cardToExport);
      }
    }
    return scannedCardsHistory;
  };

  const syncToGoogleSheet = async (showSuccessAlert = true) => {
    const cardToExport = {
      company_name: inputCompany.value,
      full_name: inputName.value,
      job_title: inputTitle.value,
      phone: inputPhone.value,
      phone_2: inputPhone2 ? inputPhone2.value : "",
      email: inputEmail.value,
      website: inputWebsite.value,
      address: inputAddress.value
    };

    if (!cardToExport.full_name && !cardToExport.company_name) {
      if (showSuccessAlert) alert("Vui lòng thực hiện trích xuất thông tin card trước khi lưu vào Google Sheet.");
      return false;
    }

    try {
      if (btnSyncGsheet) btnSyncGsheet.innerText = "⏳ Đang gửi...";
      await ApiClient.saveToGoogleSheet(cardToExport);
      if (btnSyncGsheet) {
        btnSyncGsheet.innerText = "✓ Đã lưu Sheet!";
        setTimeout(() => btnSyncGsheet.innerText = "📊 Lưu sang Google Sheet", 2000);
      }
      if (showSuccessAlert) {
        alert("✓ Đã lưu dữ liệu danh thiếp vào Google Sheet thành công!");
      }
      return true;
    } catch (e) {
      if (btnSyncGsheet) btnSyncGsheet.innerText = "❌ Lỗi lưu Sheet";
      setTimeout(() => btnSyncGsheet.innerText = "📊 Lưu sang Google Sheet", 2000);
      alert("Lỗi lưu Google Sheet: " + e.message);
      return false;
    }
  };

  if (btnSyncGsheet) {
    btnSyncGsheet.addEventListener("click", () => syncToGoogleSheet(true));
  }

  if (btnExportCsv) {
    btnExportCsv.addEventListener("click", async () => {
      const cards = getCardsToExport();
      if (cards.length === 0) {
        alert("Chưa có dữ liệu card nào để xuất CSV.");
        return;
      }
      ApiClient.downloadCSV(cards);
    });
  }

});

