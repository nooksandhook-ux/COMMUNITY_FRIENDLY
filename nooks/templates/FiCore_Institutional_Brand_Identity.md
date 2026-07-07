Here is the exact design system and color palette used to transition the platform from its stock Bootstrap roots into the premium **FiCore Institutional Brand Identity**.

You can copy and paste this directly into your documentation for future file modifications:

---

## 🎨 Core Color Palette

| Element | Hex Code | RGB Equivalent | Purpose / Brand Emotion |
| --- | --- | --- | --- |
| **Primary Navy** | `#0A1931` | `rgb(10, 25, 49)` | Institutional authority, trust, and baseline background for core dark sections (e.g., the Navbar). |
| **Rich Gold Accent** | `#C5A850` | `rgb(197, 168, 80)` | Premium achievement, rewards, trophies, and primary action highlights (e.g., Register buttons, star icons). |
| **Slate Blue** | `#2B4C7E` | `rgb(43, 76, 126)` | Interface elements requiring structural pacing emphasis (e.g., the Pacing Engine / Timer modules). |
| **Emerald Forest** | `#1E4620` | `rgb(30, 70, 32)` | Academic progress, course coverage milestone indicators, and stability (e.g., Knowledge Vault / Study modules). |

---

## 📐 Key CSS Utility Classes (Design System)

When modifying or creating new templates, use these locked-in utility classes to keep typography fluid and prevent layouts from breaking on smaller viewports:

### 1. Fluid Typography

Instead of fixed pixel sizes, these classes use CSS `clamp()` to scale perfectly between mobile and desktop windows without media-query overhead:

```css
/* Main page headers - scales dynamically between 1.8rem and 3.5rem */
.dynamic-main-title {
    font-size: clamp(1.8rem, 4vw, 3.5rem);
    word-wrap: break-word;
}

/* Card specific headers - scales safely between 1.1rem and 1.75rem */
.dynamic-card-title {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: clamp(1.1rem, 2vw, 1.75rem);
    width: 100%;
}

```

### 2. Layout & Container Safeguards

To stop custom user input or long button strings from breaking your grid layout on mobile screens:

```css
/* Forces buttons to stick to one line on desktop, but stack elegantly on mobile */
.btn-responsive-scale {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: clamp(0.8rem, 1.2vw, 1.1rem) !important;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 100%;
}

/* Locks grid card bodies to exactly 2 lines of text to maintain symmetric card heights */
.card-text-clamp {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    height: 3rem; 
}

```

### 3. Chart.js Customization Matching

Whenever generating bar or line charts via Chart.js, map the background data points to the institutional variables rather than default configurations:

* **Dataset Colors Used:** `['#2B4C7E', '#7F8C8D', '#C5A850']` *(Slate Blue, Neutral Silver, Rich Gold)*
* **Border Profiles Used:** `['#0A1931', '#34495E', '#9A7D2C']`
