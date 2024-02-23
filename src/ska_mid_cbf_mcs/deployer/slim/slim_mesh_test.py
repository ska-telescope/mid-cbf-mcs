import yaml

from ska_mid_cbf_mcs.deployer.slim import SLIM_Transceiver


class SlimMeshTest:
    def assign_links(self, mesh_config_filename: str, serial_loopback: bool):
        links = []
        with open(mesh_config_filename) as yaml_fd:
            _mesh_config = yaml.safe_load(yaml_fd)
            for fsp in _mesh_config:
                fsp_links = [
                    link for link in _mesh_config[fsp] if "[x]" not in link
                ]
                links.append(fsp_links)

        mesh_dict = dict()
        j = 0
        for fsp in links:
            for i in range(len(fsp)):
                tx, rx = fsp[i].split("->")
                if serial_loopback:
                    index = tx.split("/")[2][2:]
                    temp = tx.split("/")
                    rx = temp[0] + "/" + temp[1] + "/rx" + index
                mesh_dict[j] = [tx.strip(), rx.strip()]
                j = j + 1

        return SLIM_Transceiver.create_mesh(mesh_dict, serial_loopback)

    def run_mesh_test(self, mesh_config_filename: str, serial_loopback: bool):
        BER_PASS_TH = 8.000e-11
        t_sec = 30

        mesh = SlimMeshTest().assign_links(
            mesh_config_filename=mesh_config_filename,
            serial_loopback=serial_loopback,
        )
        test_length = t_sec
        ber_pass = BER_PASS_TH
        print("H/W Verification: Slim Mesh Links Check")
        SLIM_Transceiver.slim_mesh_links_ber_check(
            mesh, test_length, ber_pass, stop=False
        )
        print("Test finished.")
