class CanvasCropper {
  constructor(canvasElement) {
    this.canvas = canvasElement;
    this.ctx = canvasElement.getContext('2d');
    this.img = new Image();
    this.points = []; // 4 corner points
    this.activePointIndex = -1;
    this.isDragging = false;

    this.initEvents();
  }

  loadImage(src) {
    return new Promise((resolve, reject) => {
      this.img.onload = () => {
        this.resizeCanvas();
        this.resetCorners();
        this.draw();
        resolve();
      };
      this.img.onerror = reject;
      this.img.src = src;
    });
  }

  resizeCanvas() {
    const parent = this.canvas.parentElement;
    const containerWidth = parent.clientWidth || 500;
    const scale = containerWidth / this.img.width;
    this.canvas.width = containerWidth;
    this.canvas.height = this.img.height * scale;
  }

  resetCorners() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const margin = 15;
    // Top-left, Top-right, Bottom-right, Bottom-left
    this.points = [
      { x: margin, y: margin },
      { x: w - margin, y: margin },
      { x: w - margin, y: h - margin },
      { x: margin, y: h - margin }
    ];
  }

  draw() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Draw background image
    this.ctx.drawImage(this.img, 0, 0, this.canvas.width, this.canvas.height);

    if (this.points.length !== 4) return;

    // Draw polygon crop region
    this.ctx.beginPath();
    this.ctx.moveTo(this.points[0].x, this.points[0].y);
    for (let i = 1; i < 4; i++) {
      this.ctx.lineTo(this.points[i].x, this.points[i].y);
    }
    this.ctx.closePath();
    this.ctx.strokeStyle = '#06b6d4';
    this.ctx.lineWidth = 3;
    this.ctx.fillStyle = 'rgba(6, 182, 212, 0.2)';
    this.ctx.fill();
    this.ctx.stroke();

    // Draw corner handle circles
    this.points.forEach((pt, index) => {
      this.ctx.beginPath();
      this.ctx.arc(pt.x, pt.y, 10, 0, Math.PI * 2);
      this.ctx.fillStyle = (this.activePointIndex === index) ? '#06b6d4' : '#3b82f6';
      this.ctx.fill();
      this.ctx.lineWidth = 3;
      this.ctx.strokeStyle = '#ffffff';
      this.ctx.stroke();
    });
  }

  getOriginalPoints() {
    if (this.points.length !== 4) return null;
    const scaleX = this.img.width / this.canvas.width;
    const scaleY = this.img.height / this.canvas.height;
    return this.points.map(pt => [pt.x * scaleX, pt.y * scaleY]);
  }

  initEvents() {
    const getPos = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      let clientX = e.clientX;
      let clientY = e.clientY;

      if (e.touches && e.touches.length > 0) {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
      }

      // Convert display pixels to canvas internal coordinates
      const scaleX = this.canvas.width / rect.width;
      const scaleY = this.canvas.height / rect.height;

      return {
        x: (clientX - rect.left) * scaleX,
        y: (clientY - rect.top) * scaleY
      };
    };

    const startDrag = (e) => {
      const pos = getPos(e);
      this.points.forEach((pt, idx) => {
        const dist = Math.hypot(pt.x - pos.x, pt.y - pos.y);
        if (dist < 35) { // Increased hit radius to 35px for easy grabbing
          this.activePointIndex = idx;
          this.isDragging = true;
        }
      });

      if (this.isDragging) {
        this.draw();
        if (e.cancelable) e.preventDefault();
      }
    };

    const moveDrag = (e) => {
      const pos = getPos(e);

      if (!this.isDragging || this.activePointIndex === -1) {
        // Change mouse cursor style when hovering near points
        let hovering = false;
        this.points.forEach((pt) => {
          if (Math.hypot(pt.x - pos.x, pt.y - pos.y) < 35) {
            hovering = true;
          }
        });
        this.canvas.style.cursor = hovering ? 'grab' : 'crosshair';
        return;
      }

      this.canvas.style.cursor = 'grabbing';
      this.points[this.activePointIndex].x = Math.max(0, Math.min(this.canvas.width, pos.x));
      this.points[this.activePointIndex].y = Math.max(0, Math.min(this.canvas.height, pos.y));
      this.draw();
      if (e.cancelable) e.preventDefault();
    };

    const stopDrag = () => {
      this.isDragging = false;
      this.activePointIndex = -1;
      this.canvas.style.cursor = 'crosshair';
      this.draw();
    };

    this.canvas.addEventListener('mousedown', startDrag);
    this.canvas.addEventListener('mousemove', moveDrag);
    window.addEventListener('mouseup', stopDrag);

    this.canvas.addEventListener('touchstart', startDrag, { passive: false });
    this.canvas.addEventListener('touchmove', moveDrag, { passive: false });
    window.addEventListener('touchend', stopDrag);
  }
}
