# NPITS UI Code Documentation

This document serves as a comprehensive guide to understanding the UI architecture and code utilized in the NPITS (Net Profit Investment Tracking System) application. It details the core technologies, design systems, and provides code snippets outlining how to use specific UI components.

## Core UI Technologies

The NPITS frontend is built on a responsive and modern stack:

1.  **Bootstrap 5.3.0**: The primary CSS framework used for grid layouts, typography, and pre-built components (navbars, modals, buttons, alerts).
2.  **Custom CSS (Vanilla)**: Overrides and enhancements to Bootstrap, focusing on a premium aesthetic (glassmorphism, specific brand colors, and micro-animations).
3.  **Google Fonts (Inter)**: The standard font family `Inter` provides a clean, modern, and highly legible typographic hierarchy.
4.  **FontAwesome 6.0**: Used extensively for iconography across tables, buttons, and status indicators.
5.  **Animate.css**: Utility library for adding subtle entry animations (e.g., `animate__fadeIn`, `animate__slideInUp`).
6.  **Chart.js**: Utilized for rendering responsive, interactive wealth breakdown and portfolio analytics charts.

---

## 1. Global CSS Variables (Design Tokens)

The application uses CSS Custom Properties (Variables) defined in the `:root` scope of `base.html` to maintain brand consistency.

### <a name="code-section-variables"></a>Code Section: CSS Variables
```css
:root {
  --primary-color: #003D7C; /* Deep Blue, used for Navbar, Primary Buttons */
  --secondary-color: #0056b3; /* Lighter Blue, used for hover states */
  --bg-light: #f4f7f9; /* Off-white background for body */
  --text-dark: #1a1e21; /* Main text color */
  --text-muted: #6c757d; /* Subtitles and secondary text */
  --success-green: #008D4C; /* Positive indicators (Profit, Buy signals) */
  --danger-red: #D62A2D; /* Negative indicators (Loss, Sell signals) */
  --warning-yellow: #ffc107; /* Caution indicators (Hold signals) */
}

body {
  background-color: var(--bg-light);
  font-family: 'Inter', sans-serif;
  color: var(--text-dark);
}
```
**Use of this code**: 
These variables should be used whenever applying color to custom components. Instead of hardcoding `#003D7C`, always use `var(--primary-color)`.

---

## 2. Layout Structure (Base Template)

`base.html` dictates the shell of the application, incorporating the Navbar at the top and the Footer at the bottom. The dynamic content for individual pages is injected into the `<div class="container main-content">` block.

### <a name="code-section-layout"></a>Code Section: Main Container Layout
```html
<div class="container main-content">
  <!-- Django Messages Alert System -->
  {% if messages %}
    <div class="row justify-content-center">
      <div class="col-md-10">
        {% for message in messages %}
          <div class="alert alert-{{ message.tags }} alert-dismissible fade show border-0 shadow-sm mb-4" role="alert" style="border-radius: 12px;">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          </div>
        {% endfor %}
      </div>
    </div>
  {% endif %}

  <!-- Core Page Injection -->
  {% block content %}
  {% endblock %}
</div>
```
**Use of this code**:
This is standard across all pages. The `{% block content %}` is replaced by the specific page content (e.g., dashboard, strategy). The messaging system uses Bootstrap's `.alert` component augmented with custom `border-radius` and `shadow-sm` for a softer look.

---

## 3. UI Components Code

### A. Navigation Bar & Notifications

The Navbar uses Bootstrap's `navbar-expand-lg` with custom styling. It features an animated brand logo and a badge notification system for automated signals.

#### <a name="code-section-navbar"></a>Code Section: Navigation Bar
```html
<!-- Custom CSS for Navbar -->
<style>
  .navbar { background-color: var(--primary-color) !important; }
  .navbar-brand img.brand-logo { transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
  .navbar-brand:hover img.brand-logo { transform: scale(1.1) rotate(-3deg); }
  .badge-fbi {
    position: absolute; top: -2px; right: -8px;
    background-color: var(--danger-red);
    /* Notification styling */
  }
</style>

<!-- HTML Implementation -->
<li class="nav-item">
  <a class="nav-link nav-item-dashboard" href="{% url 'dashboard' %}">
    Dashboard
    {% if total_signal_count > 0 %}
      <span class="badge-fbi">{{ total_signal_count }}</span>
    {% endif %}
  </a>
</li>
```
**Use of this code**: 
The notification badge `.badge-fbi` relies on relative positioning on its parent (`.nav-item-dashboard`). It highlights when there are urgent market signals for the user. 

### B. Standard Cards and Glassmorphism

The platform heavily utilizes cards to group information. A premium "glass" effect is used for high-level summaries and hero sections.

#### <a name="code-section-cards"></a>Code Section: Cards & Glass Panels
```css
/* Standard Card Styling */
.card {
  border: none;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
}

/* Glassmorphism Panel */
.glass-panel {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}
```

```html
<!-- HTML Example of Glass Panel in Summary -->
<div class="col-md-3">
    <div class="glass-panel text-center p-3 h-100 d-flex flex-column justify-content-center">
        <h6 class="text-uppercase text-muted mb-2 fw-bold" style="font-size: 0.75rem;">Total Investment</h6>
        <h3 class="mb-0 fw-bold" style="color: var(--primary-color);">₹ {{ total_invested|floatformat:2 }}</h3>
    </div>
</div>
```
**Use of this code**:
Use `.card` for standard data containers (like tables or individual stock details). Use `.glass-panel` over complex backgrounds or for premium summary metrics at the top of a dashboard.

### C. Status Indicators (Typography)

Text colors are used semantically to denote market positions or profit/loss.

#### <a name="code-section-status"></a>Code Section: Status Indicators
```css
.status-sell { color: var(--danger-red); font-weight: 700; }
.status-buy { color: var(--success-green); font-weight: 700; }
.status-hold { color: var(--warning-yellow); font-weight: 700; }
.status-reduce { color: #fd7e14; font-weight: 700; }
```

```html
<!-- HTML Implementation -->
<td class="{% if item.action == 'BUY' %}status-buy
           {% elif item.action == 'SELL' %}status-sell
           {% elif item.action == 'REDUCE' %}status-reduce
           {% else %}status-hold{% endif %}">
    {{ item.action }}
</td>
```
**Use of this code**:
Apply these classes dynamically via Django templates to any string that represents a trading recommendation or a positive/negative numerical value.

### D. Data Tables

Tables are built using Bootstrap's table classes but improved with border-radius and specialized typography sizes to increase data density.

#### <a name="code-section-tables"></a>Code Section: Dashboard Tables
```html
<div class="table-responsive">
  <table class="table table-hover align-middle mb-0" style="font-size: 0.82rem;">
    <thead style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0;">
      <tr>
        <th class="py-3 text-uppercase text-muted fw-bold" style="font-size: 0.7rem; letter-spacing: 0.05em;">Symbol</th>
        <th class="text-center py-3 text-uppercase text-muted fw-bold" style="font-size: 0.7rem;">Action</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="fw-bold" style="color: var(--primary-color);">RELIANCE</td>
        <td class="text-center status-buy">BUY</td>
      </tr>
    </tbody>
  </table>
</div>
```
**Use of this code**:
The `<div class="table-responsive">` wrapper is critical for mobile compatibility. Table headers are styled with `.text-uppercase`, `.text-muted`, and reduced `font-size` with `letter-spacing` to look modern and read clearly.

---

## 4. JavaScript UI Enhancements

JavaScript is used minimally for DOM manipulation, primarily relying on Chart.js for data visualization and standard JS for automated background syncing.

### <a name="code-section-js"></a>Code Section: Auto-Sync Functionality
Located at the bottom of `base.html`, this snippet ensures the platform checks for data syncs in the background without user intervention.

```javascript
(function () {
  const SYNC_INTERVAL = 60 * 1000; // 1 minute
  const LAST_SYNC_KEY = 'npits_last_sync_time';
  const now = Date.now();
  const lastSync = localStorage.getItem(LAST_SYNC_KEY);

  if (!lastSync || (now - lastSync) > SYNC_INTERVAL) {
    // Trigger sync silently in the background
    fetch('/api/sync-data/')
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success' || data.status === 'skipped') {
          localStorage.setItem(LAST_SYNC_KEY, now);
        }
      })
      .catch(error => console.error('Sync failed:', error));
  }
})();
```
**Use of this code**:
Runs on every page load globally. It checks `localStorage` and triggers a Django API endpoint to pull the latest stock prices from Yahoo Finance/NSE if the 1-minute threshold has passed.

### E. Dashboard High-Level Summary Cards

Used for displaying aggregated metrics on `dashboard.html`.

#### <a name="code-section-summary-cards"></a>Code Section: Summary Cards
```html
<div class="card bg-white h-100">
    <div class="card-body p-4">
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h6 class="text-uppercase text-muted mb-0 fw-bold" style="font-size: 0.75rem;">Invested Value</h6>
            <div class="icon-shape bg-primary bg-opacity-10 text-primary rounded-circle">
                <i class="fas fa-wallet"></i>
            </div>
        </div>
        <h3 class="mb-0 fw-bold" style="color: var(--primary-color);">₹{{ total_invested|floatformat:2 }}</h3>
    </div>
</div>
```
**Use of this code**:
Provides a clean, distinct layout for key metrics. The `.icon-shape` and `bg-opacity-10` classes give a modern, tinted background to icons.

### F. Responsive Dashboard Tables

Optimized for data density and horizontal scrolling.

#### <a name="code-section-responsive-tables"></a>Code Section: Data Dense Tables
```html
<div class="table-responsive">
  <table class="table table-hover align-middle mb-0" style="font-size: 0.82rem;">
    <thead style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0;">
      <tr>
        <th class="py-3 text-uppercase text-muted fw-bold" style="font-size: 0.7rem; letter-spacing: 0.05em;">Symbol</th>
        <th class="text-center py-3 text-uppercase text-muted fw-bold" style="font-size: 0.7rem;">Action</th>
      </tr>
    </thead>
    <tbody>
      <!-- Row Data -->
    </tbody>
  </table>
</div>
```
**Use of this code**:
The `<div class="table-responsive">` wrapper is standard for mobile compatibility. Font sizes (`0.82rem`) and padding are intentionally reduced to fit more rows and columns on investment dashboards.

---
*Generated as part of the NPITS UI Documentation initiative.*
