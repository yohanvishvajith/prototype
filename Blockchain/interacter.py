from web3 import Web3
import json
import os

# --- Configuration ---
RPC_URL = "http://127.0.0.1:8545"  # Ganache or Hardhat
# Use the deployed Storage address from Ignition deployments
CONTRACT_ADDRESS = Web3.to_checksum_address("0x5FbDB2315678afecb367f032d93F642f64180aa3")
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
WALLET_ADDRESS = Web3.to_checksum_address("0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266")

# --- Connect to Blockchain ---
web3 = Web3(Web3.HTTPProvider(RPC_URL))
print("Connected:", web3.is_connected())

# --- Load ABI ---
with open("abi.json") as f:
    abi = json.load(f)

# --- Create Contract Instance ---
contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

# --- Function to Add Farmer ---
def add_farmer(
    farmer_id: str,
    nic: str,
    full_name: str,
    home_address: str,
    district: str,
    contact_number: str,
    total_paddy_area: int,
    value_eth: float = 0.0,
):
    # Build the struct tuple in the same order as FarmerInput in the Solidity contract
    farmer_input = (
        farmer_id,
        nic,
        full_name,
        home_address,
        district,
        contact_number,
        total_paddy_area,
    )

    # Convert provided ether value to wei
    value = web3.to_wei(value_eth, 'ether')

    # Optional: simulate the call locally to detect reverts before sending a transaction
    try:
        # Simulate the call locally to detect reverts before sending a transaction
        sim = contract.functions.registerFarmer(farmer_input).call({
            'from': WALLET_ADDRESS,
            'value': value
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return

    # Create transaction (include value if you want to send ETH with the call)
    tx = contract.functions.registerFarmer(farmer_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3.to_wei('20', 'gwei'),
        'value': value
    })

    # Sign transaction
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())

    # Wait for confirmation
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)

# --- Function to View Farmer ---
def view_farmer(farmer_id):
    farmer = contract.functions.getFarmer(farmer_id).call()
    print("\n--- Farmer Data ---")
    print("ID:", farmer[0])
    print("NIC:", farmer[1])
    print("Full Name:", farmer[2])
    print("Address:", farmer[3])
    print("District:", farmer[4])
    print("Contact:", farmer[5])
    print("Total Paddy Field Area:", farmer[6])


def view_all_farmers(from_block: int = 0):
    """Read past FarmerRegistered events starting at `from_block` and print each farmer.

    This uses the FarmerRegistered event emitted by the contract when a farmer is registered.
    Because the contract stores farmers in a mapping and doesn't provide an index/list function,
    we must enumerate registered farmer IDs from events.
    """
    # First, try the on-chain helper that returns all farmers (added in Storage.sol)
    try:
        farmers = contract.functions.getAllFarmers().call()
        if farmers and len(farmers) > 0:
            print("\n--- All Registered Farmers (on-chain) ---")
            for f in farmers:
                # f is a tuple matching the Farmer struct
                print("\nID:", f[0])
                print("NIC:", f[1])
                print("Full Name:", f[2])
                print("Address:", f[3])
                print("District:", f[4])
                print("Contact:", f[5])
                print("Total Paddy Field Area:", f[6])
            return
        else:
            print("getAllFarmers returned no entries; falling back to event scan.")
    except Exception as e:
        # If the function doesn't exist or call fails, fallback to scanning events
        print("getAllFarmers on-chain call failed or not available, falling back to events:", e)

    # Fallback: enumerate FarmerRegistered events (off-chain)
    try:
        # use the web3.py parameter name 'from_block'
        event_filter = contract.events.FarmerRegistered.create_filter(from_block=from_block)
        entries = event_filter.get_all_entries()
    except Exception:
        print("Falling back to eth.get_logs for FarmerRegistered events")
        event_abi = next((a for a in abi if a.get('name') == 'FarmerRegistered' and a.get('type') == 'event'), None)
        if event_abi is None:
            print("FarmerRegistered event ABI not found")
            return
        # topic for the event signature
        topic = web3.keccak(text=f"{event_abi['name']}({','.join(i['type'] for i in event_abi['inputs'])})").hex()
        logs = web3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'address': CONTRACT_ADDRESS,
            'topics': [topic]
        })
        # use process_log (web3.py naming) to decode each log
        entries = [contract.events.FarmerRegistered().process_log(log) for log in logs]

    if not entries:
        print("No FarmerRegistered events found (no farmers registered yet).")
        return

    seen = set()
    print("\n--- All Registered Farmers (events) ---")
    for ev in entries:
        farmer_id = ev['args']['id']
        if farmer_id in seen:
            continue
        seen.add(farmer_id)
        try:
            farmer = contract.functions.getFarmer(farmer_id).call()
            print("\nID:", farmer[0])
            print("NIC:", farmer[1])
            print("Full Name:", farmer[2])
            print("Address:", farmer[3])
            print("District:", farmer[4])
            print("Contact:", farmer[5])
            print("Total Paddy Field Area:", farmer[6])
        except Exception as e:
            print(f"Failed to read farmer {farmer_id}:", e)


def view_miller(miller_id: str):
    """Call getMiller and print a single miller."""
    miller = contract.functions.getMiller(miller_id).call()
    print("\n--- Miller Data ---")
    print("ID:", miller[0])
    print("Company Register Number:", miller[1])
    print("Company Name:", miller[2])
    print("Address:", miller[3])
    print("District:", miller[4])
    print("Contact:", miller[5])


def view_all_millers(from_block: int = 0):
    """List all millers using on-chain helper or by scanning MillerRegistered events."""
    # Try on-chain helper first
    try:
        millers = contract.functions.getAllMillers().call()
        if millers and len(millers) > 0:
            print("\n--- All Registered Millers (on-chain) ---")
            for m in millers:
                print("\nID:", m[0])
                print("Company Register Number:", m[1])
                print("Company Name:", m[2])
                print("Address:", m[3])
                print("District:", m[4])
                print("Contact:", m[5])
            return
        else:
            print("getAllMillers returned no entries; falling back to event scan.")
    except Exception as e:
        print("getAllMillers on-chain call failed or not available, falling back to events:", e)

    # Fallback: enumerate MillerRegistered events
    try:
        event_filter = contract.events.MillerRegistered.create_filter(from_block=from_block)
        entries = event_filter.get_all_entries()
    except Exception:
        print("Falling back to eth.get_logs for MillerRegistered events")
        event_abi = next((a for a in abi if a.get('name') == 'MillerRegistered' and a.get('type') == 'event'), None)
        if event_abi is None:
            print("MillerRegistered event ABI not found")
            return
        topic = web3.keccak(text=f"{event_abi['name']}({','.join(i['type'] for i in event_abi['inputs'])})").hex()
        logs = web3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'address': CONTRACT_ADDRESS,
            'topics': [topic]
        })
        entries = [contract.events.MillerRegistered().process_log(log) for log in logs]

    if not entries:
        print("No MillerRegistered events found (no millers registered yet).")
        return

    seen = set()
    print("\n--- All Registered Millers (events) ---")
    for ev in entries:
        miller_id = ev['args']['id']
        if miller_id in seen:
            continue
        seen.add(miller_id)
        try:
            m = contract.functions.getMiller(miller_id).call()
            print("\nID:", m[0])
            print("Company Register Number:", m[1])
            print("Company Name:", m[2])
            print("Address:", m[3])
            print("District:", m[4])
            print("Contact:", m[5])
        except Exception as e:
            print(f"Failed to read miller {miller_id}:", e)


def view_collector(collector_id: str):
    """Call getCollector and print a single collector."""
    collector = contract.functions.getCollector(collector_id).call()
    print("\n--- Collector Data ---")
    print("ID:", collector[0])
    print("NIC:", collector[1])
    print("Full Name:", collector[2])
    print("Address:", collector[3])
    print("District:", collector[4])
    print("Contact:", collector[5])


def view_all_collectors(from_block: int = 0):
    """List all collectors using on-chain helper or by scanning CollectorRegistered events."""
    # Try on-chain helper first
    try:
        collectors_list = contract.functions.getAllCollectors().call()
        if collectors_list and len(collectors_list) > 0:
            print("\n--- All Registered Collectors (on-chain) ---")
            for c in collectors_list:
                print("\nID:", c[0])
                print("NIC:", c[1])
                print("Full Name:", c[2])
                print("Address:", c[3])
                print("District:", c[4])
                print("Contact:", c[5])
            return
        else:
            print("getAllCollectors returned no entries; falling back to event scan.")
    except Exception as e:
        print("getAllCollectors on-chain call failed or not available, falling back to events:", e)

    # Fallback: enumerate CollectorRegistered events
    try:
        event_filter = contract.events.CollectorRegistered.create_filter(from_block=from_block)
        entries = event_filter.get_all_entries()
    except Exception:
        print("Falling back to eth.get_logs for CollectorRegistered events")
        event_abi = next((a for a in abi if a.get('name') == 'CollectorRegistered' and a.get('type') == 'event'), None)
        if event_abi is None:
            print("CollectorRegistered event ABI not found")
            return
        topic = web3.keccak(text=f"{event_abi['name']}({','.join(i['type'] for i in event_abi['inputs'])})").hex()
        logs = web3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'address': CONTRACT_ADDRESS,
            'topics': [topic]
        })
        entries = [contract.events.CollectorRegistered().process_log(log) for log in logs]

    if not entries:
        print("No CollectorRegistered events found (no collectors registered yet).")
        return

    seen = set()
    print("\n--- All Registered Collectors (events) ---")
    for ev in entries:
        collector_id = ev['args']['id']
        if collector_id in seen:
            continue
        seen.add(collector_id)
        try:
            c = contract.functions.getCollector(collector_id).call()
            print("\nID:", c[0])
            print("NIC:", c[1])
            print("Full Name:", c[2])
            print("Address:", c[3])
            print("District:", c[4])
            print("Contact:", c[5])
        except Exception as e:
            print(f"Failed to read collector {collector_id}:", e)


def add_collector(
    collector_id: str,
    nic: str,
    full_name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register a Collector using the contract's registerCollector function."""
    collector_input = (
        collector_id,
        nic,
        full_name,
        home_address,
        district,
        contact_number,
    )

    value = web3.to_wei(value_eth, 'ether')

    try:
        # simulate call
        contract.functions.registerCollector(collector_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return

    tx = contract.functions.registerCollector(collector_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)


def prompt_add_collector_interactive():
    print("\nEnter new collector details:")
    collector_id = input("ID: ").strip()
    nic = input("NIC: ").strip()
    full_name = input("Full name: ").strip()
    home_address = input("Home address: ").strip()
    district = input("District: ").strip()
    contact_number = input("Contact number: ").strip()
    while True:
        value_eth_s = input("Value to send with tx in ETH (default 0): ").strip()
        if value_eth_s == "":
            value_eth = 0.0
            break
        try:
            value_eth = float(value_eth_s)
            break
        except ValueError:
            print("Please enter a numeric value for ETH (e.g. 0 or 0.01).")

    confirm = input(f"Register collector {collector_id} (y/N)? ").strip().lower()
    if confirm != "y":
        print("Cancelled")
        return

    add_collector(
        collector_id,
        nic,
        full_name,
        home_address,
        district,
        contact_number,
        value_eth,
    )

# --- Interactive menu ---
def prompt_add_farmer_interactive():
    print("\nEnter new farmer details:")
    farmer_id = input("ID: ").strip()
    nic = input("NIC: ").strip()
    full_name = input("Full name: ").strip()
    home_address = input("Home address: ").strip()
    district = input("District: ").strip()
    contact_number = input("Contact number: ").strip()
    while True:
        total_paddy_area_s = input("Total paddy field area (integer): ").strip()
        try:
            total_paddy_area = int(total_paddy_area_s)
            break
        except ValueError:
            print("Please enter a valid integer for total paddy field area.")
    while True:
        value_eth_s = input("Value to send with tx in ETH (default 0): ").strip()
        if value_eth_s == "":
            value_eth = 0.0
            break
        try:
            value_eth = float(value_eth_s)
            break
        except ValueError:
            print("Please enter a numeric value for ETH (e.g. 0 or 0.01).")

    confirm = input(f"Register farmer {farmer_id} (y/N)? ").strip().lower()
    if confirm != "y":
        print("Cancelled")
        return

    add_farmer(
        farmer_id,
        nic,
        full_name,
        home_address,
        district,
        contact_number,
        total_paddy_area,
        value_eth,
    )


def add_miller(
    miller_id: str,
    company_register_number: str,
    company_name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register a Miller using the contract's registerMiller function."""
    miller_input = (
        miller_id,
        company_register_number,
        company_name,
        home_address,
        district,
        contact_number,
    )

    value = web3.to_wei(value_eth, 'ether')

    try:
        # simulate call
        contract.functions.registerMiller(miller_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return

    tx = contract.functions.registerMiller(miller_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)


def prompt_add_miller_interactive():
    print("\nEnter new miller details:")
    miller_id = input("ID: ").strip()
    company_register_number = input("Company register number: ").strip()
    company_name = input("Company name: ").strip()
    home_address = input("Home address: ").strip()
    district = input("District: ").strip()
    contact_number = input("Contact number: ").strip()
    while True:
        value_eth_s = input("Value to send with tx in ETH (default 0): ").strip()
        if value_eth_s == "":
            value_eth = 0.0
            break
        try:
            value_eth = float(value_eth_s)
            break
        except ValueError:
            print("Please enter a numeric value for ETH (e.g. 0 or 0.01).")

    confirm = input(f"Register miller {miller_id} (y/N)? ").strip().lower()
    if confirm != "y":
        print("Cancelled")
        return

    add_miller(
        miller_id,
        company_register_number,
        company_name,
        home_address,
        district,
        contact_number,
        value_eth,
    )


def record_transaction(from_party: str, to_party: str, product_type: str, quantity: int):
    """Record a transaction on-chain via recordTransaction."""
    try:
        # simulate
        contract.functions.recordTransaction(from_party, to_party, product_type, quantity).call({
            'from': WALLET_ADDRESS
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return

    tx = contract.functions.recordTransaction(from_party, to_party, product_type, quantity).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3.to_wei('20', 'gwei'),
    })
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)


def view_transaction(tx_id: int):
    """View a single transaction by ID."""
    t = contract.functions.getTransaction(tx_id).call()
    print("\n--- Transaction ---")
    print("Tx ID:", tx_id)
    print("From:", t[0])
    print("To:", t[1])
    print("Product:", t[2])
    print("Quantity:", t[3])
    print("Timestamp:", t[4])


def view_all_transactions(from_block: int = 0):
    """List all transactions using on-chain helper or scanning TransactionRecorded events."""
    try:
        txs = contract.functions.getAllTransactions().call()
        if txs and len(txs) > 0:
            print("\n--- All Transactions (on-chain) ---")
            for idx, tx in enumerate(txs, start=1):
                print("\nTx ID:", idx)
                print("From:", tx[0])
                print("To:", tx[1])
                print("Product:", tx[2])
                print("Quantity:", tx[3])
                print("Timestamp:", tx[4])
            return
        else:
            print("getAllTransactions returned no entries; falling back to events.")
    except Exception as e:
        print("getAllTransactions on-chain call failed or not available, falling back to events:", e)

    # Fallback: scan TransactionRecorded events
    try:
        event_filter = contract.events.TransactionRecorded.create_filter(from_block=from_block)
        entries = event_filter.get_all_entries()
    except Exception:
        print("Falling back to eth.get_logs for TransactionRecorded events")
        event_abi = next((a for a in abi if a.get('name') == 'TransactionRecorded' and a.get('type') == 'event'), None)
        if event_abi is None:
            print("TransactionRecorded event ABI not found")
            return
        topic = web3.keccak(text=f"{event_abi['name']}({','.join(i['type'] for i in event_abi['inputs'])})").hex()
        logs = web3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'address': CONTRACT_ADDRESS,
            'topics': [topic]
        })
        entries = [contract.events.TransactionRecorded().process_log(log) for log in logs]

    if not entries:
        print("No TransactionRecorded events found.")
        return

    print("\n--- All Transactions (events) ---")
    for ev in entries:
        args = ev['args']
        print("\nTx ID:", args['txId'])
        print("From:", args['fromParty'])
        print("To:", args['toParty'])
        print("Product:", args['productType'])
        print("Quantity:", args['quantity'])
        print("Timestamp:", args['timestamp'])


def menu_loop():
    try:
        while True:
            print("\n=== Storage Interactor ===")
            print("1) Add farmer")
            print("2) View all farmers")
            print("3) View farmer by ID")
            print("4) Add miller")
            print("5) View all millers")
            print("6) View miller by ID")
            print("7) View all collectors")
            print("8) View collector by ID")
            print("9) Add collector")
            print("10) Record transaction")
            print("11) View all transactions")
            print("12) View transaction by ID")
            print("0) Exit")
            choice = input("Choose an option: ").strip()
            if choice == "1":
                prompt_add_farmer_interactive()
            elif choice == "2":
                from_block_s = input("From block (enter for 0): ").strip()
                try:
                    from_block = int(from_block_s) if from_block_s != "" else 0
                except ValueError:
                    print("Invalid block number, using 0")
                    from_block = 0
                view_all_farmers(from_block)
            elif choice == "3":
                fid = input("Farmer ID: ").strip()
                if fid:
                    try:
                        view_farmer(fid)
                    except Exception as e:
                        print("Failed to view farmer:", e)
                else:
                    print("No ID entered")
            elif choice == "4":
                prompt_add_miller_interactive()
            elif choice == "5":
                from_block_s = input("From block (enter for 0): ").strip()
                try:
                    from_block = int(from_block_s) if from_block_s != "" else 0
                except ValueError:
                    print("Invalid block number, using 0")
                    from_block = 0
                view_all_millers(from_block)
            elif choice == "6":
                mid = input("Miller ID: ").strip()
                if mid:
                    try:
                        view_miller(mid)
                    except Exception as e:
                        print("Failed to view miller:", e)
                else:
                    print("No ID entered")
            elif choice == "7":
                from_block_s = input("From block (enter for 0): ").strip()
                try:
                    from_block = int(from_block_s) if from_block_s != "" else 0
                except ValueError:
                    print("Invalid block number, using 0")
                    from_block = 0
                view_all_collectors(from_block)
            elif choice == "8":
                cid = input("Collector ID: ").strip()
                if cid:
                    try:
                        view_collector(cid)
                    except Exception as e:
                        print("Failed to view collector:", e)
                else:
                    print("No ID entered")
            elif choice == "9":
                prompt_add_collector_interactive()
            elif choice == "10":
                print("\nEnter transaction details:")
                from_party = input("From ID: ").strip()
                to_party = input("To ID: ").strip()
                product_type = input("Product type: ").strip()
                qty_s = input("Quantity (integer): ").strip()
                try:
                    quantity = int(qty_s)
                except ValueError:
                    print("Invalid quantity")
                    continue
                confirm = input(f"Record transaction from {from_party} to {to_party} (y/N)? ").strip().lower()
                if confirm != "y":
                    print("Cancelled")
                else:
                    try:
                        record_transaction(from_party, to_party, product_type, quantity)
                    except Exception as e:
                        print("Failed to record transaction:", e)
            elif choice == "11":
                from_block_s = input("From block (enter for 0): ").strip()
                try:
                    from_block = int(from_block_s) if from_block_s != "" else 0
                except ValueError:
                    print("Invalid block number, using 0")
                    from_block = 0
                view_all_transactions(from_block)
            elif choice == "12":
                txid_s = input("Transaction ID (integer): ").strip()
                try:
                    txid = int(txid_s)
                except ValueError:
                    print("Invalid transaction ID")
                    continue
                try:
                    view_transaction(txid)
                except Exception as e:
                    print("Failed to view transaction:", e)
            elif choice == "0" or choice.lower() in ("q", "exit"):
                print("Bye")
                break
            else:
                print("Invalid choice")
    except KeyboardInterrupt:
        print("\nInterrupted — exiting.")


if __name__ == "__main__":
    menu_loop()
