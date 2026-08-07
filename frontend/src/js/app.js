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

  // Auth DOM Elements
  const loginGateScreen = document.getElementById("login-gate-screen");
  const mainAppContainer = document.getElementById("main-app-container");
  const btnLogout = document.getElementById("btn-logout");
  const userDisplayName = document.getElementById("user-display-name");

  const btnAdminOpenModal = document.getElementById("btn-admin-open-modal");
  const adminUserModal = document.getElementById("admin-user-modal");
  const btnCloseAdminModal = document.getElementById("btn-close-admin-modal");
  const adminCreateForm = document.getElementById("admin-create-form");
  const btnAdminSubmit = document.getElementById("btn-admin-submit");

  const authForm = document.getElementById("auth-form");
  const btnAuthSubmit = document.getElementById("btn-auth-submit");

  let currentUser = null;

  const dbHistoryList = document.getElementById("db-history-list");
  const btnRefreshHistory = document.getElementById("btn-refresh-history");

  const loadCardHistory = async () => {
    if (!dbHistoryList) return;
    try {
      const res = await fetch("/api/cards/history", { headers: getAuthHeaders() });
      const data = await res.json();
      dbHistoryList.innerHTML = "";
      if (!data.history || data.history.length === 0) {
        dbHistoryList.innerHTML = `<span style="font-size: 0.8rem; color: var(--text-muted);">Chưa có card nào trong CSDL</span>`;
        return;
      }
      data.history.forEach(item => {
        const cardEl = document.createElement("div");
        cardEl.style.cssText = "background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center;";
        cardEl.innerHTML = `
          <div>
            <div style="font-size: 0.85rem; font-weight: 600; color: #f8fafc;">${item.full_name || 'Chưa rõ tên'} (${item.company_name || 'Công ty N/A'})</div>
            <div style="font-size: 0.75rem; color: #94a3b8;">SĐT: ${item.phone || 'N/A'} | Quét bởi: <span style="color: #60a5fa;">${item.scanned_by || 'N/A'}</span></div>
          </div>
          <div style="font-size: 0.7rem; color: var(--text-muted); text-align: right;">${item.created_at || ''}</div>
        `;
        dbHistoryList.appendChild(cardEl);
      });
    } catch (e) {
      console.log("Load card history error:", e);
    }
  };

  if (btnRefreshHistory) {
    btnRefreshHistory.addEventListener("click", loadCardHistory);
  }

  // Check Current User Auth State (/api/auth/me)
  const getAuthHeaders = (extraHeaders = {}) => {
    const token = localStorage.getItem("auth_token");
    const headers = { ...extraHeaders };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  };

  const checkAuthState = async (loggedInUser = null) => {
    if (loggedInUser) {
      currentUser = loggedInUser;
      if (userDisplayName) userDisplayName.innerText = `${currentUser.full_name || currentUser.email || 'Đã đăng nhập'}`;
      if (btnAdminOpenModal) {
        btnAdminOpenModal.style.display = (currentUser.role === 'admin') ? "inline-block" : "none";
      }
      loginGateScreen.style.display = "none";
      mainAppContainer.style.display = "block";
      loadCardHistory();
      return;
    }

    try {
      const res = await fetch("/api/auth/me", {
        headers: getAuthHeaders()
      });
      const data = await res.json();
      if (data.authenticated && data.user) {
        currentUser = data.user;
        if (userDisplayName) userDisplayName.innerText = `${currentUser.full_name || currentUser.email || 'Đã đăng nhập'}`;
        
        // Show Admin Button if role === 'admin'
        if (btnAdminOpenModal) {
          btnAdminOpenModal.style.display = (currentUser.role === 'admin') ? "inline-block" : "none";
        }

        // Unlock Main Application
        loginGateScreen.style.display = "none";
        mainAppContainer.style.display = "block";
        loadCardHistory();
      } else {
        currentUser = null;
        if (userDisplayName) userDisplayName.innerText = "Chưa đăng nhập";
        if (btnAdminOpenModal) btnAdminOpenModal.style.display = "none";

        // Lock Main Application (Show Login Gate Screen)
        loginGateScreen.style.display = "flex";
        mainAppContainer.style.display = "none";
      }
    } catch (e) {
      console.log("Check auth state error:", e);
      loginGateScreen.style.display = "flex";
      mainAppContainer.style.display = "none";
    }
  };

  await checkAuthState();

  if (btnLogout) {
    btnLogout.addEventListener("click", async () => {
      await fetch("/api/auth/logout", { method: "POST", headers: getAuthHeaders() });
      localStorage.removeItem("auth_token");
      await checkAuthState();
      alert("Đã đăng xuất tài khoản!");
    });
  }

  // Admin Create User Modal Handlers
  if (btnAdminOpenModal) {
    btnAdminOpenModal.addEventListener("click", () => {
      adminUserModal.style.display = "flex";
    });
  }

  if (btnCloseAdminModal) {
    btnCloseAdminModal.addEventListener("click", () => {
      adminUserModal.style.display = "none";
    });
  }

  if (adminCreateForm) {
    adminCreateForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const username = document.getElementById("admin-new-username").value.trim();
      const password = document.getElementById("admin-new-password").value.trim();
      const full_name = document.getElementById("admin-new-fullname").value.trim();
      const email = document.getElementById("admin-new-email").value.trim();

      try {
        btnAdminSubmit.disabled = true;
        btnAdminSubmit.innerText = "Đang tạo...";

        const res = await fetch("/api/auth/register", {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ username, password, full_name, email, role: "user" })
        });
        const data = await res.json();

        if (res.ok && data.success) {
          alert(data.message);
          adminUserModal.style.display = "none";
          adminCreateForm.reset();
        } else {
          alert(data.detail || data.message || "Lỗi tạo tài khoản");
        }
      } catch (err) {
        alert("Lỗi kết nối server: " + err.message);
      } finally {
        btnAdminSubmit.disabled = false;
        btnAdminSubmit.innerText = "Cấp Tài Khoản Mới";
      }
    });
  }

  // Normal User Login Handler
  authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("auth-username").value.trim();
    const password = document.getElementById("auth-password").value.trim();

    try {
      btnAuthSubmit.disabled = true;
      btnAuthSubmit.innerText = "Đang xử lý...";

      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        if (data.token) {
          localStorage.setItem("auth_token", data.token);
        }
        alert(data.message);
        await checkAuthState(data.user);
      } else {
        alert(data.detail || data.message || "Tên đăng nhập hoặc mật khẩu không đúng");
      }
    } catch (err) {
      alert("Lỗi kết nối server: " + err.message);
    } finally {
      btnAuthSubmit.disabled = false;
      btnAuthSubmit.innerText = "Đăng Nhập Ngay";
    }
  });

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

  // Ensure selectedEngine is locked to v1 (Cloud AI Vision)
  selectedEngine = "v1";

  const btnOpenCamera = document.getElementById("btn-open-camera");
  const btnOpenGallery = document.getElementById("btn-open-gallery");

  if (btnOpenCamera) {
    btnOpenCamera.addEventListener("click", (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }

  if (btnOpenGallery) {
    btnOpenGallery.addEventListener("click", (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }

  // Drag & Drop & File Upload Handlers
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

  const batchQueueBanner = document.getElementById("batch-queue-banner");
  const queueStatusText = document.getElementById("queue-status-text");
  let fileQueue = [];
  let isExtracting = false;

  const updateQueueUI = () => {
    if (!batchQueueBanner || !queueStatusText) return;
    if (fileQueue.length > 0) {
      batchQueueBanner.style.display = "block";
      queueStatusText.innerText = `Còn ${fileQueue.length} ảnh trong hàng đợi... (Tự động chạy nối tiếp)`;
    } else {
      batchQueueBanner.style.display = "none";
    }
  };

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleMultipleFilesSelected(e.dataTransfer.files);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleMultipleFilesSelected(e.target.files);
    }
  });

  if (cameraInput) {
    cameraInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleMultipleFilesSelected(e.target.files);
      }
    });
  }

  const handleMultipleFilesSelected = (files) => {
    if (!files || files.length === 0) return;
    const fileList = Array.from(files);

    if (isExtracting) {
      // AI đang xử lý 1 ảnh: Tự động xếp tất cả các ảnh mới vào hàng đợi
      fileQueue.push(...fileList);
      updateQueueUI();
    } else {
      // AI rảnh: Nạp ảnh thứ 1 và xếp các ảnh còn lại vào hàng đợi
      handleFileSelected(fileList[0]);
      if (fileList.length > 1) {
        fileQueue.push(...fileList.slice(1));
        updateQueueUI();
      }
    }
  };

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
    if (isExtracting) return;
    isExtracting = true;
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
      isExtracting = false;
      btnExtract.disabled = false;
      btnExtract.innerHTML = `Trích Xuất Dữ Liệu`;

      if (fileQueue.length > 0) {
        const nextFile = fileQueue.shift();
        updateQueueUI();
        setTimeout(() => {
          handleFileSelected(nextFile);
          btnExtract.click();
        }, 600);
      }
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
      address: inputAddress.value,
      scanned_by: currentUser ? (currentUser.full_name || currentUser.email) : ""
    };

    if (!cardToExport.full_name && !cardToExport.company_name) {
      if (showSuccessAlert) alert("Vui lòng thực hiện trích xuất thông tin card trước khi lưu vào Google Sheet.");
      return false;
    }

    try {
      if (btnSyncGsheet) btnSyncGsheet.innerText = "Đang gửi...";
      await ApiClient.saveToGoogleSheet(cardToExport);
      if (btnSyncGsheet) {
        btnSyncGsheet.innerText = "Đã lưu Sheet!";
        setTimeout(() => btnSyncGsheet.innerText = "Lưu sang Google Sheet", 2000);
      }
      if (showSuccessAlert) {
        alert("Đã lưu dữ liệu danh thiếp vào Google Sheet thành công!");
      }
      return true;
    } catch (e) {
      if (btnSyncGsheet) btnSyncGsheet.innerText = "Lỗi lưu Sheet";
      setTimeout(() => btnSyncGsheet.innerText = "Lưu sang Google Sheet", 2000);
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

