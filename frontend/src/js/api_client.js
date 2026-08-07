const API_BASE = "";

class ApiClient {
  static async getSampleCards() {
    try {
      const res = await fetch(`${API_BASE}/api/sample-cards`);
      return await res.json();
    } catch (e) {
      console.error("Error fetching sample cards:", e);
      return { samples: [] };
    }
  }

  static async extractCardInfo({ file, sampleFilename, engine, apiKey, cropPoints }) {
    const formData = new FormData();
    if (file) {
      formData.append("file", file);
    }
    if (sampleFilename) {
      formData.append("sample_filename", sampleFilename);
    }
    formData.append("engine", engine || "v1");
    if (apiKey) {
      formData.append("api_key", apiKey);
    }
    if (cropPoints) {
      formData.append("crop_points_json", JSON.stringify(cropPoints));
    }

    try {
      const res = await fetch(`${API_BASE}/api/extract`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const text = await res.text();
        let errMsg = text;
        try {
          const errJson = JSON.parse(text);
          errMsg = errJson.detail || errJson.error || text;
        } catch (_) {}
        throw new Error(errMsg);
      }
      return await res.json();
    } catch (e) {
      throw e;
    }
  }

  static async downloadVCard(cardData) {
    try {
      const res = await fetch(`${API_BASE}/api/export/vcard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cardData)
      });
      const blob = await res.blob();
      const name = (cardData.full_name || "contact").replace(/\s+/g, "_");
      this.triggerDownload(blob, `${name}.vcf`);
    } catch (e) {
      alert("Lỗi xuất file vCard: " + e.message);
    }
  }

  static async downloadExcel(cardList) {
    try {
      const res = await fetch(`${API_BASE}/api/export/excel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cardList)
      });
      const blob = await res.blob();
      this.triggerDownload(blob, "scanned_cards.xlsx");
    } catch (e) {
      alert("Lỗi xuất file Excel: " + e.message);
    }
  }

  static async downloadCSV(cardList) {
    try {
      const res = await fetch(`${API_BASE}/api/export/csv`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cardList)
      });
      const blob = await res.blob();
      this.triggerDownload(blob, "scanned_cards.csv");
    } catch (e) {
      alert("Lỗi xuất file CSV: " + e.message);
    }
  }

  static async saveToGoogleSheet(cardData) {
    try {
      const res = await fetch(`${API_BASE}/api/save-google-sheet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cardData)
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.detail || data.error || "Lỗi lưu vào Google Sheet");
      }
      return data;
    } catch (e) {
      throw e;
    }
  }

  static async exportToGoogleSheet(cardList, webhookUrl) {
    try {
      const res = await fetch(`${API_BASE}/api/export/google-sheet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cards: cardList, webhook_url: webhookUrl })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Lỗi lưu vào Google Sheet");
      }
      return data;
    } catch (e) {
      throw e;
    }
  }


  static triggerDownload(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }
}
