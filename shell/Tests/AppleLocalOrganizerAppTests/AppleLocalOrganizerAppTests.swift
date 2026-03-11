import Foundation
import Testing
@testable import AppleLocalOrganizerApp

@Test
func responseEnvelopeDecoding() throws {
        let data = """
        {"ok":true,"result":{"shell_supported":true,"ai_supported":false,"reason":"compat","os_version":"15.0"}}
        """.data(using: .utf8)!
        let decoded = try JSONDecoder().decode(ResponseEnvelope<EnvironmentStatus>.self, from: data)
        #expect(decoded.ok)
        #expect(decoded.result?.reason == "compat")
}

@Test
func scanTargetPath() {
    #expect(ScanTarget.downloads.defaultPath.hasSuffix("/Downloads"))
}
