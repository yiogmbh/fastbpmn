variable "PLATFORMS" {
  default = ["linux/amd64"]
}

target "build" {
  output = ["type=docker"]
}
