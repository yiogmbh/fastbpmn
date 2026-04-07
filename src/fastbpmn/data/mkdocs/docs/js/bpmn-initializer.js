async function load_bpmnviewer() {
    for (const node of document.querySelectorAll(".bpmn-viewer")) {

        const node_id = '#' + node.id;
        const bpmn_b64 = node.dataset.bpmn;
        const bpmn_xml = atob(bpmn_b64)

        /* Make sure that there is no placeholder text anymore */
        node.innerHTML = '';

        let bpmnViewer = new BpmnJS({
            container: node_id
        });

        try {
            console.log("Initializing BPMN Viewer for div " + node_id);
            bpmnViewer.importXML(bpmn_xml).then(({warnings}) =>{

                var canvas = bpmnViewer.get('canvas');

                // zoom to fit full viewport
                canvas.zoom('fit-viewport');

            });
        } catch (err) {
            console.error('could not import BPMN 2.0 diagram', err);
        }
    }
}

load_bpmnviewer().then(x => {
    console.log("BPMN Diagrams initialized")
})
