function showPanel(name) {
    const panels = document.getElementById('panel-right').children;
    const panel = document.getElementById('panel-' + name);
    for (const elem of panels)
        elem.style.display = "none";
    panel.style.display = "flex";
}
