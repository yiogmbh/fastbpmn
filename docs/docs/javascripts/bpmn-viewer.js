(function () {
    const viewers = new Map();

    function showError(container, message) {
        container.classList.add("bpmn-viewer--error");
        container.textContent = message;
    }

    function bpmnDecode(element) {

        const businessElement = element.businessObject;
        const businessObject = element.businessObject;
        const bpmnType = businessElement.$type;

        return {
            id: element.id,
            bpmnId: businessElement.id,
            bpmnName: businessElement.name,
            bpmnType: bpmnType,
            camundaType: businessObject.get('camunda:type'),
            camundaTopic: businessObject.get('camunda:topic'),
            getTitle: function () {
                switch (this.bpmnType) {
                    case "bpmn:StartEvent":
                        return `${this.bpmnName} (process start)`;
                    case "bpmn:EndEvent":
                        return `${this.bpmnName} (process end)`;
                }
                return `${this.bpmnName} (topic='${this.camundaTopic}')`;
            }
        }
    }


    function bpmnViewerConfig(container) {
        const script = container.querySelector("script.bpmn-viewer-config");

        if (!script) {
            return {}
        }

        return JSON.parse(script.textContent.trim());
    }

    function bpmnFindCodeSnippets(config, container, snippetFilename, topic) {
        const searchSpace = container.parentElement;

        const snippetConfig = config.snippets
            .filter((snippet) => {
                return snippet.filename === snippetFilename && snippet.topic === topic
            })
            .at(0);

        // return nothing if no snippetConfig is found
        if (!snippetConfig) {
            return [];
        }

        const divs = [...document.querySelectorAll("div.language-python.highlight")]
            .filter((el) => {
                const filename = el.querySelector("span.filename");
                return filename?.textContent.trim() === snippetFilename;
            });


        // figure out the pre
        function _transform(div) {

            const codeContainer = [...div.getElementsByClassName("md-code__content")]
                .find(Boolean);
            const codeIdentifier = codeContainer.parentNode?.id;
            const codeSnippetNo = codeIdentifier.split("_").pop();
            const lineNumbers = snippetConfig.lineHighlights;

            return {
                el: div,
                codeContainer: codeContainer,
                codeIdentifier: codeIdentifier,
                lineNoId: function (no) {
                    return `__span-${codeSnippetNo}-${no}`
                },
                codeLineNoId: function (no) {
                    return `__codelineno-${codeSnippetNo}-${no}`
                },
                gotoHref: function () {
                    const otherLInkElement = codeContainer.querySelector(`#${this.codeLineNoId(lineNumbers.at(0))}`);
                    const linkElement = document.getElementById(this.lineNoId(lineNumbers.at(0)))
                    const link = linkElement.id;
                    console.log("goto elem:", linkElement, link);
                    console.log("other link", otherLInkElement);
                    return `#${link}`;
                },
                goto: function () {
                    const lastElement = codeContainer.querySelector(`#${this.codeLineNoId(lineNumbers.slice(-1))}`);

                    lastElement.parentNode.scrollTo({
                        top: lastElement.offsetTop,
                        left: 0,
                        behavior: 'smooth'
                    });
                },
                highlight: function () {

                    var lineNoIds = lineNumbers.map(this.lineNoId);

                    [...codeContainer.children]
                        .filter((el) => lineNoIds.includes(el.id))
                        .forEach((el) => {
                            el.classList.add("hll");
                        })
                },
                reset: function () {
                    [...codeContainer.children].forEach((el) => {
                        el.classList.remove("hll");
                    })
                }
            };
        }

        return divs.map(_transform);
    }

    async function render(container) {
        if (viewers.has(container)) {
            viewers.get(container).destroy();
            viewers.delete(container);
            console.log("destroyes for reasons")
        }

        container.classList.remove("bpmn-viewer--error");
        const canvas = container.querySelector(".bpmn-viewer__canvas");
        const selection = container.querySelector(".bpmn-viewer__selection");
        if (!canvas || !selection) {
            showError(container, "Unable to render this BPMN diagram: invalid viewer container");
            return;
        }
        const config = bpmnViewerConfig(container);

        console.log(config);

        //canvas.textContent = "Loading process diagram...";
        try {
            const response = await fetch(container.dataset.bpmnSrc);
            if (!response.ok) {
                throw new Error(`BPMN file returned HTTP ${response.status}`);
            }

            const xml = await response.text();
            const viewer = new BpmnJS({
                container: canvas
            });
            await viewer.importXML(xml);

            viewer.get("canvas").zoom("fit-viewport");
            viewers.set(container, viewer);
            container.setAttribute("aria-label", container.dataset.bpmnTitle);
            viewer.on("element.click", function (event) {
                const element = event.element;
                const details = bpmnDecode(element);
                const snippets = bpmnFindCodeSnippets(config, container, "example.py", details.camundaTopic)

                snippets.forEach((snippet) => {
                    snippet.reset();
                    snippet.highlight();
                })

                container.dataset.selectedElement = details.id;

                const newTitle = document.createElement('a');
                newTitle.setAttribute('href', snippets.at(0).gotoHref());


                newTitle.innerText = details.getTitle();


                //const newTitle = `<a href="${snippets.at(0).gotoHref()}">${details.getTitle()}</a>`
                selection.innerHTML = '';
                selection.appendChild(newTitle);


                const title = element.businessObject.name || element.id;
                container.dataset.selectedElement = element.id;
                container.setAttribute("aria-label", `${container.dataset.bpmnTitle}: ${title}`);

                console.log("snippets", snippets)
                console.log(snippets)

                console.log(element);
                console.log(details);
            });
        } catch (error) {
            showError(container, `Unable to render this BPMN diagram: ${error.message}`);
        }
    }

    function renderAll() {
        document.querySelectorAll(".bpmn-viewer").forEach(render);
    }

    if (typeof document$ !== "undefined") {
        document$.subscribe(renderAll);
    } else {
        document.addEventListener("DOMContentLoaded", renderAll);
    }
})();
