import os
import subprocess


class ConanWrapper:
    """
    ConanWrapper provides a Python interface to the shell commands required to download Conan packages.
    There is a Python API, but it is not documented, and according to: https://github.com/conan-io/conan/issues/6315
    ``The python api is not documented nor stable. It might change at any time and break your scripts.``
    This class can be updated to use the Python API if/when that makes sense.

    :param folder: destination path for downloaded (deployed) conan packages.
    :type folder: string
    """

    def __init__(self, folder):
        self._folder = folder
        this_dir = os.path.dirname(os.path.abspath(__file__))
        self.profiles_dir = os.path.join(this_dir, "conan_profiles")

    @staticmethod
    def version():
        """
        Returns conan version.
        """
        return subprocess.getoutput("conan --version").strip("Conan version ")

    @staticmethod
    def search_local_cache():
        """
        Searches local cache for package recipes and binaries.
        """
        return subprocess.getoutput("conan search")

    @staticmethod
    def clear_local_cache():
        """
        Removes all packages and binaries from the local cache.
        """
        return subprocess.getoutput('conan remove "*" --force')

    def download_package(
        self, pkg_name, version, user, channel, profile, timeout=60
    ):
        """
        Run conan install to download the conan package and deploy it to the folder specified at construction.

        :param pkg_name: conan package name
        :type pkg_name: string
        :param version: conan package version number
        :type version: string
        :param user: user name of conan package
        :type user: string
        :param channel: conan package channel name
        :type channel: string
        :param profile: name of text file containing the conan profile used to deploy the download package
        :type profile: string
        :param timeout: download timeout in seconds
        :type timeout: int
        """
        try:
            subprocess.run(
                f"conan install -if {self._folder} {pkg_name}/{version}@{user}/{channel} -g deploy -pr {profile}",
                timeout=timeout,
                shell=True,
            )
        except subprocess.TimeoutExpired:
            print(f"Download of Conan package {pkg_name} timed out.")
        except Exception as e:
            print(f"Download of Conan package {pkg_name} - exception {e}")
