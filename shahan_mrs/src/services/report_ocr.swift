import Foundation
import CoreML
import Vision
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
let handler = VNImageRequestHandler(url: url, options: [:])
do {
    // A headless Streamlit process may not have access to an accelerator.
    if #available(macOS 14.0, *) {
        for (stage, devices) in try request.supportedComputeStageDevices {
            for device in devices {
                if case .cpu = device {
                    request.setComputeDevice(device, for: stage)
                    break
                }
            }
        }
    } else {
        request.usesCPUOnly = true
    }
    try handler.perform([request])
    for observation in request.results ?? [] {
        if let text = observation.topCandidates(1).first { print(text.string) }
    }
} catch {
    FileHandle.standardError.write(Data(String(describing: error).utf8))
    exit(1)
}
