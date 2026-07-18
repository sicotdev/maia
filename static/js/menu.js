function showPanel(name) {
    const panels = document.getElementById('panel-right').children;
    let panel = document.getElementById('panel-' + name);
    
    //Toggle panel for other buttons than 'chat'
    if (panel.style.display == 'flex')
        panel = document.getElementById('panel-chat'); // we show chat instead

    for (const elem of panels)
        elem.style.display = "none";
    panel.style.display = "flex";
}
