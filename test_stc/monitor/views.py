from contextlib import contextmanager

import paramiko
from django.shortcuts import render
from django.http import JsonResponse
from .forms import SSHConnectionForm
import threading
import time


@contextmanager
def ssh_connection(hostname, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password)
    try:
        yield client
    finally:
        client.close()


def execute_ssh_command(client, command):
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode()


def ssh_connect(request):
    if request.method == "POST":
        form = SSHConnectionForm(request.POST)
        if form.is_valid():
            hostname = form.cleaned_data["hostname"]
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            port = form.cleaned_data["port"]

            request.session["ssh_client_details"] = {
                "hostname": hostname,
                "username": username,
                "password": password,
                "port": port,
            }
            return render(request, "monitor/monitor.html", {"form": form})
    else:
        form = SSHConnectionForm()
    return render(request, "monitor/connect.html", {"form": form})


def get_output(request):
    if request.method == "GET":
        ssh_details = request.session.get("ssh_client_details", None)
        if ssh_details:
            hostname = ssh_details["hostname"]
            username = ssh_details["username"]
            password = ssh_details["password"]
            port = ssh_details["port"]

            with ssh_connection(hostname, port, username, password) as client:
                output = execute_ssh_command(
                    client, f"echo {password} | sudo -S lsof -i -P -n | grep LISTEN"
                )

            output_lines = output.strip().split("\n")
            output_data = [line.split() for line in output_lines]
            return JsonResponse({"output": output_data, "ip_address": hostname})

    return JsonResponse({"error": "Invalid request"}, status=400)
