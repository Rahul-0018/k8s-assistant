variable "tenancy_ocid" {
  description = "Oracle Cloud Tenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "Oracle Cloud User OCID"
  type        = string
}

variable "fingerprint" {
  description = "API Key Fingerprint"
  type        = string
}

variable "private_key_path" {
  description = "Path to private API key"
  type        = string
}

variable "region" {
  description = "Oracle Cloud Region"
  type        = string
  default     = "us-ashburn-1"
}

variable "compartment_id" {
  description = "Compartment OCID"
  type        = string
}

variable "image_ocid" {
  description = "OS Image OCID (Oracle Linux 8/9)"
  type        = string
  default     = "ocid1.image.oc1.iad.aaaaaaaaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" # Update this
}

variable "ssh_public_key" {
  description = "Path to SSH public key"
  type        = string
}

variable "ssh_private_key" {
  description = "Path to SSH private key"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed for SSH"
  type        = string
  default     = "0.0.0.0/0" # Change to your IP for security
}

variable "groq_api_key" {
  description = "Groq API Key"
  type        = string
  sensitive   = true
}
