# Quick CSS Class Reference

## 🎨 Layout Classes

### Containers
```html
<div class="container">        <!-- Max-width wrapper with padding -->
<div class="stack">           <!-- Vertical spacing with gaps -->
```

### Page Structure
```html
<div class="page-header">     <!-- Flex header with title + actions -->
  <div>
    <h1 class="page-title">   <!-- Large gradient heading -->
    <p class="page-subtitle"> <!-- Muted subtitle text -->
  </div>
  <div class="page-actions">  <!-- Button group container -->
</div>
```

## 🎯 Component Classes

### Panels & Cards
```html
<div class="panel">           <!-- Main surface container -->
<div class="panel compact">   <!-- Less padding -->
<div class="panel flat">      <!-- No shadow -->

<div class="card">            <!-- Article/content card -->
  <div class="card-thumbnail-container">  <!-- Image wrapper -->
    <img class="article-thumbnail">       <!-- Cover image -->
  </div>
  <div class="card-body">                <!-- Card content -->
    <h3 class="card-title">              <!-- Card heading -->
    <p class="card-description">         <!-- Card text -->
    <a class="card-link">                <!-- Card link -->
</div>
```

### Buttons
```html
<button class="btn">          <!-- Default button -->
<button class="btn btn-sm">   <!-- Small button -->
<button class="btn btn-primary">   <!-- Blue gradient -->
<button class="btn btn-success">   <!-- Green -->
<button class="btn btn-warning">   <!-- Amber -->
<button class="btn btn-danger">    <!-- Rose -->
```

### Forms
```html
<form class="stack">
  <div class="form-grid">     <!-- 2-column layout -->
    <div class="form-group">  <!-- Label + input wrapper -->
      <label>
      <input type="text">
      <div class="help-text"> <!-- Muted helper text -->
    </div>
  </div>
  
  <div class="form-actions">  <!-- Button row -->
    <button type="submit">
  </div>
</form>
```

### Tables
```html
<div class="table-responsive"> <!-- Scrollable wrapper -->
  <table class="table">        <!-- Styled table -->
    <thead>
    <tbody>
</div>
```

## 🎭 Utility Classes

### Badges
```html
<span class="badge">          <!-- Default badge -->
<span class="badge badge-success">
<span class="badge badge-warning">
<span class="badge badge-danger">
```

### Text Utilities
```html
<div class="text-center">     <!-- Center align -->
<div class="text-muted">      <!-- Muted color -->
<div class="text-bright">     <!-- Bright white -->
```

### Spacing Utilities
```html
<div class="mb-0">  <!-- Margin bottom: 0 -->
<div class="mb-1">  <!-- Margin bottom: 8px -->
<div class="mb-2">  <!-- Margin bottom: 16px -->
<div class="mb-3">  <!-- Margin bottom: 24px -->

<div class="mt-0">  <!-- Margin top: 0 -->
<div class="mt-1">  <!-- Margin top: 8px -->
<div class="mt-2">  <!-- Margin top: 16px -->
<div class="mt-3">  <!-- Margin top: 24px -->
```

### Divider
```html
<div class="divider">         <!-- Horizontal rule -->
```

## 🌟 Special Classes

### Navigation
```html
<header class="topbar">
  <div class="topbar-inner">
    <a class="brand">
      <span class="brand-badge">
      <span class="brand-title">
    </a>
    <nav class="nav">
      <a class="active">      <!-- Active nav item -->
```

### Hero Section
```html
<div class="hero">            <!-- Hero container -->
  <h1>                        <!-- Large title -->
  <p>                         <!-- Description -->
  <div class="hero-actions">  <!-- Button group -->
```

### Article Grid
```html
<section class="article-grid"> <!-- Responsive card grid -->
  <div class="card">          <!-- Individual cards -->
```

### Media Grid
```html
<div class="media-grid">      <!-- Image/video grid -->
  <img>
  <video>
```

### Search
```html
<section class="article-search"> <!-- Search wrapper -->
  <form class="search-form">     <!-- Search form -->
```

## 📱 Responsive Behavior

### Breakpoints
- **860px**: Forms switch to 1-column, page headers stack
- **760px**: Mobile nav menu activates
- **480px**: Full-width buttons, single article column

### Mobile Menu
```html
<input class="nav-toggle" type="checkbox" id="nav-toggle">
<label class="nav-toggle-label" for="nav-toggle">Menu</label>
<nav class="nav">  <!-- Hidden by default, shown when checked -->
```

## 🎨 CSS Variables (Custom Properties)

### Colors
```css
--bg              /* Background dark */
--text            /* Main text color */
--text-bright     /* Pure white */
--muted           /* Dimmed text */
--border          /* Border color */

--primary         /* Blue */
--success         /* Green */
--warning         /* Amber */
--danger          /* Rose */
```

### Sizing
```css
--container       /* Max content width: 1220px */
--font-base       /* Base font size: 16px */

--radius          /* Border radius: 16px */
--radius-lg       /* Large radius: 20px */
--radius-sm       /* Small radius: 12px */
```

### Shadows
```css
--shadow          /* Default shadow */
--shadow-lg       /* Large shadow */
--shadow-soft     /* Soft shadow */
--shadow-btn      /* Button shadow */
```

## 💡 Common Patterns

### Empty State
```html
<div class="panel" style="text-align: center; padding: 48px;">
  <h3>No items found</h3>
  <p class="help-text">Try adjusting your filters.</p>
</div>
```

### Left-Border Accent
```html
<div class="panel flat" 
     style="border-left: 3px solid rgba(90, 148, 255, 0.50);">
  ...
</div>
```

### Full-Width Form Field
```html
<div class="form-group" style="grid-column: 1 / -1;">
  <label>Description</label>
  <textarea></textarea>
</div>
```

### Centered Content
```html
<div class="panel" style="text-align: center;">
  <h1>Title</h1>
  <div class="hero-actions" style="justify-content: center;">
    ...
  </div>
</div>
```

## 🔍 Selector Reference

### Hover States
All interactive elements have hover states:
- Buttons: lift + glow
- Cards: lift + border color
- Links: color change
- Nav items: background + border

### Focus States
`:focus-visible` styling for keyboard navigation with blue outline ring

### Active States
`.active` class for current navigation item with gradient background

---

**Pro Tip**: Use browser DevTools to inspect elements and see computed CSS values!
