#!/usr/bin/env python3
"""
VAST AI Python Client

A wrapper around the vastai CLI for programmatic access to VAST AI
cloud GPU instances. Designed for the Agentic Science Worker.

Usage:
    from vast_client import VastClient

    vast = VastClient()
    offers = vast.search_offers(gpu_name="RTX_4090", max_price=0.40)
    instance = vast.create_instance(offers[0]['id'], image="nvidia/cuda:12.2.0-devel-ubuntu22.04")
    vast.wait_until_ready(instance['id'])
    ssh_cmd = vast.get_ssh_command(instance['id'])
    # ... use instance ...
    vast.destroy_instance(instance['id'])
"""

import subprocess
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class InstanceInfo:
    """Information about a VAST AI instance."""
    id: int
    status: str
    gpu_name: str
    ssh_host: Optional[str]
    ssh_port: Optional[int]
    dph: float  # dollars per hour
    start_time: Optional[str]

    @property
    def ssh_command(self) -> Optional[str]:
        if self.ssh_host and self.ssh_port:
            return f"ssh -p {self.ssh_port} root@{self.ssh_host}"
        return None


class VastClientError(Exception):
    """Exception raised for VAST AI client errors."""
    pass


class VastClient:
    """
    Python client for VAST AI cloud GPU instances.

    Provides methods to search, create, manage, and destroy instances
    on the VAST AI marketplace.
    """

    def __init__(self, api_key_path: str = "~/.config/vastai/api_key"):
        """
        Initialize the VAST AI client.

        Args:
            api_key_path: Path to the API key file
        """
        self.api_key_path = Path(api_key_path).expanduser()
        self._verify_setup()

    def _verify_setup(self):
        """Verify vastai CLI is installed and API key exists."""
        # Check CLI
        result = subprocess.run(["which", "vastai"], capture_output=True, text=True)
        if result.returncode != 0:
            raise VastClientError("vastai CLI not found. Install with: pip install vastai")

        # Check API key
        if not self.api_key_path.exists():
            raise VastClientError(f"API key not found at {self.api_key_path}")

    def _run_vastai(self, args: List[str], raw: bool = True) -> Dict[str, Any]:
        """
        Run a vastai command and return parsed output.

        Args:
            args: Command arguments (without 'vastai' prefix)
            raw: Whether to request raw JSON output

        Returns:
            Parsed JSON response or {'output': stdout} for non-JSON commands
        """
        cmd = ["vastai"] + args
        if raw and "--raw" not in args:
            cmd.append("--raw")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise VastClientError(f"Command failed: {' '.join(cmd)}\nError: {result.stderr}")

        # Try to parse as JSON
        output = result.stdout.strip()
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"output": output}
        return {}

    def get_balance(self) -> float:
        """
        Get current account balance.

        Returns:
            Account balance in dollars
        """
        result = self._run_vastai(["show", "user"])
        if isinstance(result, dict) and "credit" in result:
            return float(result["credit"])
        return 0.0

    def search_offers(
        self,
        gpu_name: Optional[str] = None,
        min_gpu_ram: int = 16,
        max_price: float = 1.0,
        limit: int = 10,
        sort_by: str = "dph+"
    ) -> List[Dict[str, Any]]:
        """
        Search for available GPU instances.

        Args:
            gpu_name: Specific GPU model (e.g., "RTX_4090", "A100")
            min_gpu_ram: Minimum GPU RAM in GB
            max_price: Maximum price per hour in dollars
            limit: Maximum number of results
            sort_by: Sort order (dph+ = cheapest first)

        Returns:
            List of available offers
        """
        query_parts = [
            "rentable=True",
            f"gpu_ram>={min_gpu_ram}",
            f"dph<={max_price}",
        ]

        if gpu_name:
            # Handle spaces in GPU names
            gpu_name_query = gpu_name.replace(" ", "_")
            query_parts.append(f"gpu_name={gpu_name_query}")

        query = " ".join(query_parts)

        result = self._run_vastai(["search", "offers", query, "-o", sort_by])

        if isinstance(result, list):
            return result[:limit]
        return []

    def create_instance(
        self,
        offer_id: int,
        image: str = "nvidia/cuda:12.2.0-devel-ubuntu22.04",
        disk_gb: int = 50,
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new instance from an offer.

        Args:
            offer_id: The offer ID from search_offers()
            image: Docker image to use
            disk_gb: Disk space in GB
            label: Optional label for the instance

        Returns:
            Instance creation response with 'new_contract' as instance ID
        """
        args = [
            "create", "instance", str(offer_id),
            "--image", image,
            "--disk", str(disk_gb),
            "--ssh"
        ]

        if label:
            args.extend(["--label", label])

        result = self._run_vastai(args)
        return result

    def show_instances(self) -> List[InstanceInfo]:
        """
        Get list of all current instances.

        Returns:
            List of InstanceInfo objects
        """
        result = self._run_vastai(["show", "instances"])

        instances = []
        if isinstance(result, list):
            for item in result:
                instances.append(InstanceInfo(
                    id=item.get("id", 0),
                    status=item.get("actual_status", "unknown"),
                    gpu_name=item.get("gpu_name", "unknown"),
                    ssh_host=item.get("ssh_host"),
                    ssh_port=item.get("ssh_port"),
                    dph=item.get("dph_total", 0),
                    start_time=item.get("start_date")
                ))
        return instances

    def get_instance(self, instance_id: int) -> Optional[InstanceInfo]:
        """
        Get information about a specific instance.

        Args:
            instance_id: The instance ID

        Returns:
            InstanceInfo or None if not found
        """
        instances = self.show_instances()
        for inst in instances:
            if inst.id == instance_id:
                return inst
        return None

    def wait_until_ready(
        self,
        instance_id: int,
        timeout: int = 300,
        poll_interval: int = 10
    ) -> bool:
        """
        Wait for an instance to be ready for SSH.

        Args:
            instance_id: The instance ID
            timeout: Maximum wait time in seconds
            poll_interval: Time between status checks

        Returns:
            True if ready, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            instance = self.get_instance(instance_id)

            if instance is None:
                raise VastClientError(f"Instance {instance_id} not found")

            if instance.status == "running" and instance.ssh_host:
                # Also verify SSH is accessible
                if self._check_ssh_ready(instance):
                    return True

            time.sleep(poll_interval)

        return False

    def _check_ssh_ready(self, instance: InstanceInfo) -> bool:
        """Check if SSH connection is possible."""
        if not instance.ssh_host or not instance.ssh_port:
            return False

        # Quick SSH check
        cmd = [
            "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-p", str(instance.ssh_port),
            f"root@{instance.ssh_host}",
            "echo ready"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def get_ssh_command(self, instance_id: int) -> Optional[str]:
        """
        Get the SSH command for an instance.

        Args:
            instance_id: The instance ID

        Returns:
            SSH command string or None
        """
        instance = self.get_instance(instance_id)
        if instance:
            return instance.ssh_command
        return None

    def run_command(
        self,
        instance_id: int,
        command: str,
        timeout: int = 3600
    ) -> Dict[str, Any]:
        """
        Run a command on an instance via SSH.

        Args:
            instance_id: The instance ID
            command: Command to run
            timeout: Command timeout in seconds

        Returns:
            Dict with 'stdout', 'stderr', 'returncode'
        """
        instance = self.get_instance(instance_id)
        if not instance or not instance.ssh_host:
            raise VastClientError(f"Instance {instance_id} not accessible")

        cmd = [
            "ssh", "-o", "ConnectTimeout=10",
            "-o", "StrictHostKeyChecking=no",
            "-p", str(instance.ssh_port),
            f"root@{instance.ssh_host}",
            command
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    def upload_file(
        self,
        instance_id: int,
        local_path: str,
        remote_path: str = "/root/"
    ) -> bool:
        """
        Upload a file to an instance.

        Args:
            instance_id: The instance ID
            local_path: Local file path
            remote_path: Remote destination path

        Returns:
            True if successful
        """
        instance = self.get_instance(instance_id)
        if not instance or not instance.ssh_host:
            raise VastClientError(f"Instance {instance_id} not accessible")

        cmd = [
            "scp", "-o", "StrictHostKeyChecking=no",
            "-P", str(instance.ssh_port),
            local_path,
            f"root@{instance.ssh_host}:{remote_path}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def download_file(
        self,
        instance_id: int,
        remote_path: str,
        local_path: str = "./"
    ) -> bool:
        """
        Download a file from an instance.

        Args:
            instance_id: The instance ID
            remote_path: Remote file path
            local_path: Local destination path

        Returns:
            True if successful
        """
        instance = self.get_instance(instance_id)
        if not instance or not instance.ssh_host:
            raise VastClientError(f"Instance {instance_id} not accessible")

        cmd = [
            "scp", "-o", "StrictHostKeyChecking=no",
            "-P", str(instance.ssh_port),
            f"root@{instance.ssh_host}:{remote_path}",
            local_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    def destroy_instance(self, instance_id: int) -> bool:
        """
        Destroy an instance (stops billing).

        Args:
            instance_id: The instance ID

        Returns:
            True if successful
        """
        result = self._run_vastai(["destroy", "instance", str(instance_id)])
        return True  # vastai destroy doesn't return meaningful output

    def estimate_cost(self, offer: Dict[str, Any], hours: float) -> float:
        """
        Estimate cost for running a job.

        Args:
            offer: Offer dict from search_offers()
            hours: Expected runtime in hours

        Returns:
            Estimated cost in dollars
        """
        dph = offer.get("dph_total", offer.get("dph", 0))
        return dph * hours

    def find_best_offer(
        self,
        gpu_name: Optional[str] = None,
        min_gpu_ram: int = 16,
        max_price: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best (cheapest) offer matching criteria.

        Args:
            gpu_name: Specific GPU model
            min_gpu_ram: Minimum GPU RAM in GB
            max_price: Maximum price per hour

        Returns:
            Best offer or None if none available
        """
        offers = self.search_offers(
            gpu_name=gpu_name,
            min_gpu_ram=min_gpu_ram,
            max_price=max_price,
            limit=1
        )
        return offers[0] if offers else None


# Convenience functions for quick access

def quick_gpu_test():
    """Quick test to verify VAST AI access works."""
    client = VastClient()

    print(f"Balance: ${client.get_balance():.2f}")

    offers = client.search_offers(max_price=0.30, limit=3)
    print(f"Found {len(offers)} cheap offers:")
    for offer in offers:
        print(f"  {offer.get('gpu_name')}: ${offer.get('dph_total', 0):.2f}/hr")

    return True


if __name__ == "__main__":
    # Run quick test when executed directly
    quick_gpu_test()
