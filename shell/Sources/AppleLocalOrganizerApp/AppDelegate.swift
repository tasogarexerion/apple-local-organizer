import AppKit
import Foundation

@MainActor
final class AgentAppDelegate: NSObject, NSApplicationDelegate {
    private let textServiceProvider = TextServiceProvider()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.servicesProvider = textServiceProvider
    }

    func application(_ sender: NSApplication, openFiles filenames: [String]) {
        Task { @MainActor in
            await AppState.shared.handleOpenedFiles(filenames)
        }
        sender.reply(toOpenOrPrint: .success)
    }
}
