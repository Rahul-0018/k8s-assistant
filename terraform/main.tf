terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# Get availability domains
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# VCN
resource "oci_core_vcn" "chatbot_vcn" {
  cidr_block     = "10.0.0.0/16"
  compartment_id = var.compartment_id
  display_name   = "groq-chatbot-vcn"
  dns_label      = "chatbot"
}

# Internet Gateway
resource "oci_core_internet_gateway" "igw" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.chatbot_vcn.id
  display_name   = "chatbot-igw"
}

# Route Table
resource "oci_core_route_table" "public_rt" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.chatbot_vcn.id
  display_name   = "public-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
}

# Security List (Firewall Rules)
resource "oci_core_security_list" "public_sl" {
  compartment_id = var.compartment_id
  vcn_id         = oci_core_vcn.chatbot_vcn.id
  display_name   = "chatbot-security-list"

  # SSH access
  ingress_security_rules {
    protocol  = "6" # TCP
    source    = var.allowed_ssh_cidr
    tcp_options { min = 22 max = 22 }
  }

  # HTTP
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    tcp_options { min = 80 max = 80 }
  }

  # HTTPS
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    tcp_options { min = 443 max = 443 }
  }

  # App port (for direct access)
  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    tcp_options { min = 8000 max = 8000 }
  }

  # Kubernetes API
  ingress_security_rules {
    protocol  = "6"
    source    = var.allowed_ssh_cidr
    tcp_options { min = 6443 max = 6443 }
  }

  # Allow all outbound
  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

# Public Subnet
resource "oci_core_subnet" "public_subnet" {
  cidr_block        = "10.0.1.0/24"
  compartment_id    = var.compartment_id
  vcn_id            = oci_core_vcn.chatbot_vcn.id
  display_name      = "public-subnet"
  route_table_id    = oci_core_route_table.public_rt.id
  security_list_ids = [oci_core_security_list.public_sl.id]
  dns_label         = "public"
}

# Always-Free Compute Instance (AMD)
resource "oci_core_instance" "k8s_node" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = var.compartment_id
  display_name        = "groq-chatbot-k8s-node"
  shape               = "VM.Standard.E2.1.Micro" # Always free!

  shape_config {
    ocpus         = 1
    memory_in_gbs = 1
  }

  source_details {
    source_type = "image"
    source_id   = var.image_ocid
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public_subnet.id
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = file(var.ssh_public_key)
  }

  extended_metadata = {
    user_data = base64encode(templatefile("${path.module}/cloud-init.sh", {
      groq_api_key = var.groq_api_key
    }))
  }
}

# Outputs
output "public_ip" {
  value = oci_core_instance.k8s_node.public_ip
  description = "Public IP of the K8s node"
}

output "ssh_command" {
  value = "ssh -i ${var.ssh_private_key} opc@${oci_core_instance.k8s_node.public_ip}"
  description = "SSH command to connect to the node"
}
