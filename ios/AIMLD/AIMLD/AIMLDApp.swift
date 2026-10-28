import SwiftUI

@main
struct AIMLDApp: App {
    @StateObject private var model = LicenseViewModel()
    var body: some Scene {
        WindowGroup {
            Group {
                if model.isLicensed { MenuView(model: model) } else { LicenseView(model: model) }
            }
            .task { await model.validateSavedActivation() }
        }
    }
}
