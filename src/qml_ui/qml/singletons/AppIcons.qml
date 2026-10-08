import QtQuick

pragma Singleton

QtObject {
    id: icons

    readonly property string folder: Qt.resolvedUrl("../../resources/icons/folder.svg")
    readonly property string dashboard: Qt.resolvedUrl("../../resources/icons/dashboard.svg")
    readonly property string archive: Qt.resolvedUrl("../../resources/icons/archive.svg")
    readonly property string trash: Qt.resolvedUrl("../../resources/icons/trash.svg")
    readonly property string document: Qt.resolvedUrl("../../resources/icons/document.svg")
    readonly property string shield: Qt.resolvedUrl("../../resources/icons/shield.svg")
    readonly property string settings: Qt.resolvedUrl("../../resources/icons/settings.svg")
    readonly property string sun: Qt.resolvedUrl("../../resources/icons/sun.svg")
    readonly property string moon: Qt.resolvedUrl("../../resources/icons/moon.svg")
    readonly property string refresh: Qt.resolvedUrl("../../resources/icons/refresh.svg")
    readonly property string check: Qt.resolvedUrl("../../resources/icons/check.svg")
    readonly property string alert: Qt.resolvedUrl("../../resources/icons/alert.svg")
    readonly property string cross: Qt.resolvedUrl("../../resources/icons/cross.svg")
    readonly property string info: Qt.resolvedUrl("../../resources/icons/info.svg")
    readonly property string copy: Qt.resolvedUrl("../../resources/icons/copy.svg")
    readonly property string chevronDown: Qt.resolvedUrl("../../resources/icons/chevron-down.svg")
    readonly property string chevronRight: Qt.resolvedUrl("../../resources/icons/chevron-right.svg")
    readonly property string search: Qt.resolvedUrl("../../resources/icons/search.svg")
    readonly property string download: Qt.resolvedUrl("../../resources/icons/download.svg")
}
