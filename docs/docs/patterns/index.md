---
icon: lucide/blocks
---
# Patterns and Integrations

This section collects patterns for applications that use fastbpmn alongside a
process engine and a BPMN-aware user interface.

## User tasks and forms

An external task can hand work to a user task when human input is required.
Keep the form data as a versioned process-variable contract, validate it with
an input model in the next handler, and use a business error when the data is
valid but cannot be accepted by the business process.

## Display the current process state

The documentation viewer can be used as a starting point for an application
that displays a running process. The application needs two inputs:

1. BPMN XML for the process definition.
2. Element IDs representing completed and currently active work from the
   process-engine API.

A UI-specific integration can then pass those inputs to a viewer:

```javascript
renderProcess({
  bpmnXml,
  activeElementIds: ["BuildGreeting"],
  completedElementIds: ["StartEvent"],
});
```

The example above is an integration contract, not a fastbpmn runtime API. The
mapping from engine history/activity responses to BPMN element IDs remains
engine-specific.

For a fixed demonstration, the [deep-dive example](../deep-dive/index.md)
shows the same process without requiring a live engine.

## Embed a BPMN viewer

An application embedding a BPMN viewer should keep diagram rendering separate
from task-worker communication:

- Fetch and cache the BPMN XML using the application backend.
- Fetch process state through the backend rather than exposing engine
  credentials in the browser.
- Pass only the diagram XML and display state to the browser viewer.
- Treat element selection as read-only navigation and never enable model
  editing unless the application explicitly requires it.
