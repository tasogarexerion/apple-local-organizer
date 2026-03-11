import AppKit
import Foundation

final class TextServiceProvider: NSObject {
    private final class ServiceResultBox: @unchecked Sendable {
        let semaphore = DispatchSemaphore(value: 0)
        var result: SummaryResult?
        var errorMessage: String?
    }

    private let bridge = PythonBridge()

    @objc(summarizeSelectedText:userData:error:)
    func summarizeSelectedText(
        _ pasteboard: NSPasteboard,
        userData _: String?,
        error: AutoreleasingUnsafeMutablePointer<NSString?>?
    ) {
        guard let selectedText = pasteboard.string(forType: .string)?
            .trimmingCharacters(in: .whitespacesAndNewlines),
            !selectedText.isEmpty else {
            error?.pointee = "選択テキストがありません。" as NSString
            return
        }

        let defaults = UserDefaults.standard
        let style = defaults.string(forKey: "defaultStyle") ?? "bullets"
        let length = defaults.string(forKey: "defaultLength") ?? "short"
        let instruction = defaults.string(forKey: "extraInstruction")?
            .trimmingCharacters(in: .whitespacesAndNewlines)
        let normalizedInstruction = instruction?.isEmpty == false ? instruction : nil

        let box = ServiceResultBox()

        // macOS Services expects a synchronous result on the service pasteboard.
        Task.detached(priority: .userInitiated) { [bridge] in
            defer { box.semaphore.signal() }
            do {
                box.result = try await bridge.summarizeText(
                    text: selectedText,
                    style: style,
                    length: length,
                    instruction: normalizedInstruction
                )
            } catch {
                box.errorMessage = error.localizedDescription
            }
        }

        box.semaphore.wait()

        guard let result = box.result else {
            error?.pointee = (box.errorMessage ?? "選択テキストの要約に失敗しました。") as NSString
            return
        }

        pasteboard.clearContents()
        pasteboard.setString(result.summary_text, forType: .string)

        Task { @MainActor in
            await AppState.shared.recordServiceSummary(result)
        }
    }
}
