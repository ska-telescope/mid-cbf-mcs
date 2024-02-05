import time

import tqdm
from beautifultable import BeautifulTable
from tango import DeviceProxy

GBPS = 25.78125 * 64 / 66


class SLIM_Transceiver_PHY:
    def __init__(
        self, tx_name: str, rx_name: str, link_name: str = None
    ) -> None:
        self.tx_slim = DeviceProxy(tx_name)
        self.rx_slim = DeviceProxy(rx_name)
        self.tx_name = tx_name
        self.rx_name = rx_name
        self.link_name = link_name if link_name else f"{tx_name}=>{rx_name}"


def create_mesh(mesh: dict, loopback: bool) -> list:
    print("SLIM Mesh Links:")
    slim_links = []

    for i in range(len(mesh)):
        if loopback:
            link = SLIM_Transceiver_PHY(
                mesh.get(i)[0], mesh.get(i)[1], f"{mesh.get(i)[0]}->LOOPBACK"
            )
        else:
            link = SLIM_Transceiver_PHY(
                mesh.get(i)[0],
                mesh.get(i)[1],
                f"{mesh.get(i)[0]}->{mesh.get(i)[1]}",
            )
        print(f"{link.tx_name}   =>   {link.rx_name}    as   {link.link_name}")
        link.rx_slim.initialize_connection(loopback)
        rx_idle_word = link.rx_slim.idle_ctrl_word
        tx_idle_word = link.tx_slim.idle_ctrl_word
        if rx_idle_word == tx_idle_word:
            slim_links.append(link)
        else:
            print(
                "ERROR: Idle words do not match. Ensure slim_mesh_config.yaml matches physical mesh configuration.\nRx=["
                + str(rx_idle_word)
                + "]\nTx=["
                + str(tx_idle_word)
                + "]"
            )
            exit(-1)

    return slim_links


def slim_mesh_links_ber_check(
    slim_links, test_length=30, ber_pass=5.000e-09, stop=False
):
    t_sleep = 2
    with tqdm.tqdm(
        desc="SLIM Mesh Check",
        total=test_length,
        unit="seconds",
        initial=0.0,
        colour="green",
    ) as pbar:
        for _ in range(0, test_length, t_sleep):
            time.sleep(t_sleep)
            pbar.update(t_sleep)

    print(f"SLIM Mesh Links BER Summary After ~{test_length} seconds:")
    print(slim_mesh_links_ber_check_summary(slim_links, ber_pass))
    print("SLIM Mesh Links Details:")
    print(slim_table(slim_links))
    # Shut down the SLIM XCVRs
    if stop:
        stop_slim_links(slim_links)
    return slim_links


def slim_mesh_links_ber_check_summary(slim_links, ber_pass):
    status_dict = {}

    for link in slim_links:
        rx_word_count = link.rx_slim.read_counters[0]
        rx_idle_word_count = link.rx_slim.read_counters[2]
        rx_idle_error_count = link.rx_slim.read_counters[3]
        if not rx_idle_word_count:
            rx_wer = "NaN"
            rx_status = "Unknown"
        elif not rx_idle_error_count:
            rx_wer = f"better than {1/rx_idle_word_count:.0e}"
            rx_status = "Passed"
        else:
            rx_wr_float = rx_idle_error_count / rx_idle_word_count
            rx_wer = f"{rx_wr_float:.3e}"
            if rx_wr_float < ber_pass:
                rx_status = "Passed"
            else:
                rx_status = "Failed"
        rx_words = rx_word_count + rx_idle_word_count

        # create SLIM Mesh Link health summary:
        status_dict[f"{link.link_name}"] = {}
        status_dict[f"{link.link_name}"]["rx_wer"] = rx_wer
        status_dict[f"{link.link_name}"]["rx_status"] = rx_status
        status_dict[f"{link.link_name}"]["rx_rate_gbps"] = (
            rx_idle_word_count / rx_words * GBPS
        )

    # print SLIM Mesh Link health summary:
    print(f"BER check pass threshold: {ber_pass:.3e}")
    for link in status_dict.items():
        rx_board_status = "Passed"
        print(link)
        link_status = link[1]["rx_status"]
        if link_status == "Failed":
            rx_board_status = "Failed"
            print(f"Slim Mesh Link status: {link_status}")
        else:
            print(f"Slim Mesh Link Status: {rx_board_status}")
    from pprint import pprint

    pprint(status_dict)


def slim_table(slim_links):
    table = BeautifulTable(maxwidth=180)
    table.columns.header = [
        "Link",
        "CDR locked\n(lost)",
        "Block Aligned\n(lost)",
        "Tx Data (Gbps)\n(words)",
        "Tx Idle (Gbps)",
        "Rx Data\n(Gbps)\n(words)",
        "Rx Idle\n(Gbps)",
        "Idle Error\nCount",
        "Word\nError Rate",
    ]
    for link in slim_links:
        tx_word_count = link.tx_slim.read_counters[0]
        rx_word_count = link.rx_slim.read_counters[0]
        tx_idle_word_count = link.tx_slim.read_counters[2]
        rx_idle_word_count = link.rx_slim.read_counters[2]
        rx_idle_error_count = link.rx_slim.read_counters[3]
        tx_words = tx_word_count + tx_idle_word_count
        rx_words = rx_word_count + rx_idle_word_count
        if not rx_idle_word_count:
            rx_wer = "NaN"
        elif not rx_idle_error_count:
            rx_wer = f"better than {1/rx_idle_word_count:.0e}"
        else:
            rx_wer = f"{rx_idle_error_count/rx_idle_word_count:.3e}"

        data_row = (
            link.link_name,
            f"{link.rx_slim.debug_alignment_and_lock_status[3]} ({link.rx_slim.debug_alignment_and_lock_status[2]})",
            f"{link.rx_slim.debug_alignment_and_lock_status[1]} ({link.rx_slim.debug_alignment_and_lock_status[0]})",
            f"{link.tx_slim.link_occupancy * GBPS:.2f}\n({tx_word_count})",
            f"{tx_idle_word_count/tx_words * GBPS:.2f}",
            f"{link.rx_slim.link_occupancy * GBPS:.2f}\n({rx_word_count})",
            f"{rx_idle_word_count/rx_words * GBPS:.2f}",
            f"{rx_idle_error_count} /\n{rx_words:.2e}",
            rx_wer,
        )
        table.rows.append(data_row)
    return table


def stop_slim_links(slim_links):
    for link in slim_links:
        # Put the Rx device back into loopback, and reset the PHY Controllers
        link.rx_slim.initialize_connection(True)
        link.tx_slim.Reset()
        link.rx_slim.Reset()
        print(f"{link.link_name} stopped")
