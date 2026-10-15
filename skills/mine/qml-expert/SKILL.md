---
name: qml-expert
description: Expert instructions and critical safety guidelines for editing and formatting QML files on Omarchy Linux.
---

# QML Expert Guidelines

When acting as a QML Expert, you MUST adhere to the following guidelines and safety protocols to ensure robust, performant, and stable UI layouts.

## Mandatory Tooling

Whenever you modify QML files, you MUST use the following tools before finalizing your changes:

1. **QML Linting:** Always run `/usr/lib/qt6/bin/qmllint <file>` to check for syntax and type errors.
2. **QML Formatting:** Always run `/usr/lib/qt6/bin/qmlformat -i <file>` to format the code according to standard Qt guidelines.

## CRITICAL: QML Anti-Patterns (System Stability Warning)

**WARNING:** Breaking these layout rules can cause severe system instability. 

* **NEVER** use horizontal anchors (`anchors.left`, `anchors.right`, `anchors.horizontalCenter`) on an item that is a child of a `Row`.
* **NEVER** use vertical anchors (`anchors.top`, `anchors.bottom`, `anchors.verticalCenter`) on an item that is a child of a `Column`.

**Why?**
Positioning elements like `Row` and `Column` automatically calculate the positions of their children along their respective axes. If a child simultaneously attempts to dictate its own position along that layout axis using anchors, it creates an infinite layout invalidation loop. This loop will rapidly max out the GPU driver, crash the Wayland compositor, and trigger a Kernel Panic (Linux Blue Screen of Death `drm_panic`).

## Examples: Incorrect vs. Correct Layouts

### 1. Horizontal Layouts (`Row` and `RowLayout`)

**INCORRECT (DO NOT DO THIS):** Using horizontal anchors inside a `Row`.
```qml
Row {
    width: 300
    
    Text {
        text: "Left Item"
    }
    
    Text {
        text: "Right Item"
        // CRITICAL BUG: This will cause an infinite loop and kernel panic!
        anchors.right: parent.right 
    }
}
```

**CORRECT:** Using a spacer item with `Layout.fillWidth` inside a `RowLayout`.
```qml
import QtQuick.Layouts

RowLayout {
    width: 300
    
    Text {
        text: "Left Item"
    }
    
    Item {
        // This acts as a spacer, filling the available width
        // and safely pushing the next item to the right.
        Layout.fillWidth: true 
    }
    
    Text {
        text: "Right Item"
    }
}
```

### 2. Vertical Layouts (`Column` and `ColumnLayout`)

**INCORRECT (DO NOT DO THIS):** Using vertical anchors inside a `Column`.
```qml
Column {
    height: 400
    
    Text {
        text: "Top Item"
    }
    
    Text {
        text: "Bottom Item"
        // CRITICAL BUG: This will cause an infinite loop and kernel panic!
        anchors.bottom: parent.bottom 
    }
}
```

**CORRECT:** Using a spacer item with `Layout.fillHeight` inside a `ColumnLayout`.
```qml
import QtQuick.Layouts

ColumnLayout {
    height: 400
    
    Text {
        text: "Top Item"
    }
    
    Item {
        // This spacer fills the available height safely.
        Layout.fillHeight: true 
    }
    
    Text {
        text: "Bottom Item"
    }
}
```
