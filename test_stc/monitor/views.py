import paramiko
from django.shortcuts import render
from django.http import JsonResponse
from .forms import SSHConnectionForm
from paramiko.ssh_exception import SSHException, NoValidConnectionsError, AuthenticationException

import threading
import time

class SSHConnectionManager:
    _instances = {}

    def __new__(cls, session_key, hostname=None, port=None, username=None, password=None):
        if session_key not in cls._instances or not cls._instances[session_key]:
            instance = super(SSHConnectionManager, cls).__new__(cls)
            instance.client = paramiko.SSHClient()
            instance.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                instance.client.connect(hostname, port=port, username=username, password=password)
                cls._instances[session_key] = instance
            except (NoValidConnectionsError, SSHException, AuthenticationException) as e:
                cls._instances[session_key] = None
                raise e
            except Exception as e:
                cls._instances[session_key] = None
                raise e
        return cls._instances[session_key]

    def get_client(self):
        if self.client is None:
            raise SSHException("SSH connection is not established.")
        return self.client

    @classmethod
    def close(cls, session_key):
        if session_key in cls._instances and cls._instances[session_key]:
            cls._instances[session_key].client.close()
            del cls._instances[session_key]
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

            try:
                SSHConnectionManager(
                    session_key=request.session.session_key,
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=password
                )
                return render(request, "monitor/monitor.html", {"form": form})

            except (NoValidConnectionsError, SSHException, AuthenticationException) as e:
                form.add_error(None, f"SSH connection failed: {str(e)}")
                return render(request, "monitor/connect.html", {"form": form})

    else:
        form = SSHConnectionForm()
    return render(request, "monitor/connect.html", {"form": form})


def execute_ssh_command(client, command):
    try:
        stdin, stdout, stderr = client.exec_command(command)
        return stdout.read().decode()
    except SSHException as e:
        raise e
    except Exception as e:
        raise e

def get_output(request):
    if request.method == "GET":
        ssh_details = request.session.get("ssh_client_details", None)
        if ssh_details:
            session_key = request.session.session_key
            try:
                hostname = ssh_details["hostname"]
                username = ssh_details["username"]
                password = ssh_details["password"]
                port = ssh_details["port"]
                ssh_manager = SSHConnectionManager(
                    session_key=request.session.session_key,
                    hostname=hostname,
                    port=port,
                    username=username,
                    password=password
                )
                client = ssh_manager.get_client()
                output = execute_ssh_command(
                    client, f"echo {ssh_details['password']} | sudo -S lsof -i -P -n | grep LISTEN"
                )
                output_lines = output.strip().split("\n")
                output_data = [line.split() for line in output_lines]
                return JsonResponse({"output": output_data, "ip_address": ssh_details["hostname"]})

            except (NoValidConnectionsError, SSHException, AuthenticationException) as e:
                return JsonResponse({"error": f"SSH operation failed: {str(e)}"})
            except Exception as e:
                return JsonResponse({"error": f"SSH operation failed: {str(e)}"})
    return JsonResponse({"error": "Invalid request"}, status=400)