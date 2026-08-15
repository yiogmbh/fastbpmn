variable "PLATFORMS" {
  default = ["linux/arm64"]
}

target "build" {
  output = ["type=docker"]
}
