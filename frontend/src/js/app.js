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
  const liveCameraModal = document.getElementById("live-camera-modal");
  const cameraStreamVideo = document.getElementById("camera-stream-video");
  const btnCloseCameraModal = document.getElementById("btn-close-camera-modal");
  const btnSnapPhoto = document.getElementById("btn-snap-photo");

  let activeMediaStream = null;

  const stopCameraStream = () => {
    if (activeMediaStream) {
      activeMediaStream.getTracks().forEach(track => track.stop());
      activeMediaStream = null;
    }
    if (cameraStreamVideo) {
      cameraStreamVideo.srcObject = null;
    }
    if (liveCameraModal) {
      liveCameraModal.style.display = "none";
    }
  };

  const startCameraStream = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Trình duyệt của bạn không hỗ trợ camera trực tiếp.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false
      });

      activeMediaStream = stream;
      if (cameraStreamVideo) {
        cameraStreamVideo.srcObject = stream;
        await cameraStreamVideo.play();
      }
      if (liveCameraModal) {
        liveCameraModal.style.display = "flex";
      }
    } catch (err) {
      console.warn("Camera getUserMedia error:", err);
      stopCameraStream();
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        alert("Trình duyệt chưa được cấp quyền truy cập Camera/Webcam. Vui lòng cho phép quyền Camera trên thanh địa chỉ trình duyệt.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        alert("Không tìm thấy thiết bị Camera / Webcam trên máy tính của bạn.");
      } else {
        alert("Không thể khởi chạy Camera: " + (err.message || err.name));
      }
    }
  };

  if (btnOpenCamera) {
    btnOpenCamera.addEventListener("click", (e) => {
      e.stopPropagation();
      startCameraStream();
    });
  }

  if (btnSnapPhoto) {
    btnSnapPhoto.addEventListener("click", () => {
      if (!cameraStreamVideo || !activeMediaStream) return;

      const videoWidth = cameraStreamVideo.videoWidth || 1280;
      const videoHeight = cameraStreamVideo.videoHeight || 720;

      const tempCanvas = document.createElement("canvas");
      tempCanvas.width = videoWidth;
      tempCanvas.height = videoHeight;
      const ctx = tempCanvas.getContext("2d");
      ctx.drawImage(cameraStreamVideo, 0, 0, videoWidth, videoHeight);

      tempCanvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], `card_camera_${Date.now()}.jpg`, { type: "image/jpeg" });
          addFilesToQueue([file]);
        }
        stopCameraStream();
      }, "image/jpeg", 0.95);
    });
  }

  if (btnCloseCameraModal) {
    btnCloseCameraModal.addEventListener("click", stopCameraStream);
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

  const cardQueueContainer = document.getElementById("card-queue-container");
  const cardQueueThumbs = document.getElementById("card-queue-thumbs");
  const queueBadgeCount = document.getElementById("queue-badge-count");
  const btnClearQueue = document.getElementById("btn-clear-queue");

  let cardQueueList = [];
  let activeCardId = null;
  let cardIdCounter = 1;
  let isExtracting = false;

  const renderQueueThumbs = () => {
    if (!cardQueueContainer || !cardQueueThumbs) return;

    if (cardQueueList.length === 0) {
      cardQueueContainer.style.display = "none";
      cardQueueThumbs.innerHTML = "";
      if (queueBadgeCount) queueBadgeCount.innerText = "(0 thẻ)";
      return;
    }

    cardQueueContainer.style.display = "block";
    const extractedCount = cardQueueList.filter(c => c.status === "extracted").length;
    if (queueBadgeCount) queueBadgeCount.innerText = `(${extractedCount}/${cardQueueList.length} đã đọc)`;

    cardQueueThumbs.innerHTML = "";

    cardQueueList.forEach((card, idx) => {
      const thumbEl = document.createElement("div");
      const isActive = (card.id === activeCardId);
      const isDone = (card.status === "extracted");

      thumbEl.style.cssText = `
        position: relative;
        flex: 0 0 auto;
        width: 76px;
        height: 54px;
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;
        border: 2px solid ${isActive ? '#3b82f6' : isDone ? '#10b981' : 'rgba(255, 255, 255, 0.25)'};
        background: #0f172a;
        box-shadow: ${isActive ? '0 0 10px rgba(59, 130, 246, 0.6)' : '0 2px 6px rgba(0,0,0,0.3)'};
        transition: all 0.2s ease;
      `;

      thumbEl.innerHTML = `
        <img src="${card.dataUrl}" style="width: 100%; height: 100%; object-fit: cover;" />
        <div style="position: absolute; bottom: 0; left: 0; right: 0; background: ${isDone ? 'rgba(16, 185, 129, 0.85)' : 'rgba(0,0,0,0.75)'}; color: #fff; font-size: 0.65rem; text-align: center; padding: 2px 0; font-weight: 600;">
          ${isDone ? '✓ Đã đọc' : `Thẻ #${idx + 1}`}
        </div>
      `;

      thumbEl.addEventListener("click", () => {
        switchActiveCard(card.id);
      });

      cardQueueThumbs.appendChild(thumbEl);
    });
  };

  const switchActiveCard = (cardId) => {
    const card = cardQueueList.find(c => c.id === cardId);
    if (!card) return;

    activeCardId = card.id;
    selectedFile = card.file;
    selectedSampleName = null;

    // Nạp ảnh lên canvas cropper để người dùng kéo 4 góc
    cropper.loadImage(card.dataUrl);

    // Nếu thẻ đã trích xuất trước đó, nạp dữ liệu cũ để người dùng review & lưu
    if (card.status === "extracted" && card.extractedData) {
      renderSingleResult(card.extractedData);
    } else {
      clearForm();
    }

    renderQueueThumbs();
  };

  const addFilesToQueue = (files) => {
    if (!files || files.length === 0) return;
    const fileList = Array.from(files);
    let loadedCount = 0;
    const firstIndex = cardQueueList.length;

    fileList.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const newCard = {
          id: `card_${Date.now()}_${cardIdCounter++}`,
          file: file,
          dataUrl: e.target.result,
          name: file.name || `Thẻ #${cardQueueList.length + 1}`,
          status: "pending",
          extractedData: null
        };
        cardQueueList.push(newCard);
        loadedCount++;

        if (loadedCount === fileList.length) {
          if (!activeCardId || !cardQueueList.find(c => c.id === activeCardId)) {
            switchActiveCard(cardQueueList[firstIndex].id);
          } else {
            renderQueueThumbs();
          }
        }
      };
      reader.readAsDataURL(file);
    });
  };

  if (btnClearQueue) {
    btnClearQueue.addEventListener("click", () => {
      if (confirm("Xóa tất cả các thẻ trong danh sách hàng đợi?")) {
        cardQueueList = [];
        activeCardId = null;
        selectedFile = null;
        clearForm();
        renderQueueThumbs();
      }
    });
  }

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFilesToQueue(e.dataTransfer.files);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      addFilesToQueue(e.target.files);
    }
  });

  if (cameraInput) {
    cameraInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        addFilesToQueue(e.target.files);
      }
    });
  }

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
    const activeCard = cardQueueList.find(c => c.id === activeCardId);
    if (!activeCard && !selectedFile) {
      alert("Vui lòng chọn hoặc tải 1 thẻ danh thiếp để trích xuất.");
      return;
    }

    isExtracting = true;
    btnExtract.disabled = true;
    btnExtract.innerHTML = `<span class="spinner"></span> Đang trích xuất...`;

    const cropPoints = cropper.getOriginalPoints();
    const apiKey = apiKeyInput ? apiKeyInput.value.trim() : null;

    try {
      const res = await ApiClient.extractCardInfo({
        file: activeCard ? activeCard.file : selectedFile,
        sampleFilename: selectedSampleName,
        engine: selectedEngine,
        apiKey: apiKey,
        cropPoints: cropPoints
      });

      const extractedResult = res.result || res.v1 || res;

      // Lưu kết quả trích xuất vào thẻ đang chọn và đánh dấu đã đọc
      if (activeCard) {
        activeCard.extractedData = extractedResult;
        activeCard.status = "extracted";
      }

      renderSingleResult(extractedResult);
      renderQueueThumbs();
    } catch (e) {
      alert("Lỗi trích xuất: " + e.message);
    } finally {
      isExtracting = false;
      btnExtract.disabled = false;
      btnExtract.innerHTML = `Trích Xuất Dữ Liệu`;
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
    const cardToExport = {
      company_name: inputCompany.value,
      full_name: inputName.value,
      job_title: inputTitle.value,
      phone: inputPhone.value,
      phone_2: inputPhone2 ? inputPhone2.value : "",
      email: inputEmail.value,
      website: inputWebsite.value,
      address: inputAddress.value,
      scanned_by: currentUser ? (currentUser.full_name || currentUser.email || "CITARES Admin") : "CITARES Admin"
    };

    if (scannedCardsHistory.length === 0) {
      if (cardToExport.full_name || cardToExport.company_name) {
        scannedCardsHistory.push(cardToExport);
      }
    } else {
      // Ensure all history cards have scanned_by populated
      scannedCardsHistory.forEach(c => {
        if (!c.scanned_by) {
          c.scanned_by = currentUser ? (currentUser.full_name || currentUser.email || "CITARES Admin") : "CITARES Admin";
        }
      });
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
      scanned_by: currentUser ? (currentUser.full_name || currentUser.email || "CITARES Admin") : "CITARES Admin"
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

