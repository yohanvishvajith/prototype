from web3 import Web3
import json
import os

# --- Configuration ---
# Two separate RPC URLs for two independent blockchains
ACCOUNTS_RPC_URL = "http://127.0.0.1:8545"  # UserAccounts blockchain
OPERATIONS_RPC_URL = "http://127.0.0.1:8546"  # Operations blockchain

PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
WALLET_ADDRESS = Web3.to_checksum_address("0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266")

# --- Connect to UserAccounts Blockchain ---
web3_accounts = Web3(Web3.HTTPProvider(ACCOUNTS_RPC_URL))
print("UserAccounts Blockchain Connected:", web3_accounts.is_connected())

# --- Connect to Operations Blockchain ---
web3_operations = Web3(Web3.HTTPProvider(OPERATIONS_RPC_URL))
print("Operations Blockchain Connected:", web3_operations.is_connected())

# --- Load UserAccounts ABI ---
with open("user-accounts-abi.json") as f:
    user_accounts_abi = json.load(f)

# Load UserAccounts contract address
try:
    with open("user-accounts-abi-address.json") as f:
        user_accounts_address = json.load(f)["address"]
except FileNotFoundError:
    user_accounts_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"  # default
    print("Warning: user-accounts-abi-address.json not found, using default address")

user_accounts_contract = web3_accounts.eth.contract(
    address=Web3.to_checksum_address(user_accounts_address),
    abi=user_accounts_abi
)

# --- Load Operations ABI ---
with open("operations-abi.json") as f:
    operations_abi = json.load(f)

# Load Operations contract address
try:
    with open("operations-abi-address.json") as f:
        operations_address = json.load(f)["address"]
except FileNotFoundError:
    operations_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"  # default
    print("Warning: operations-abi-address.json not found, using default address")

operations_contract = web3_operations.eth.contract(
    address=Web3.to_checksum_address(operations_address),
    abi=operations_abi
)

print(f"UserAccounts Contract: {user_accounts_address}")
print(f"Operations Contract: {operations_address}")

# Legacy compatibility - Keep web3 and contract references for backward compatibility
web3 = web3_accounts  # Default to accounts blockchain
contract = user_accounts_contract  # Default to user accounts contract


# ========================================
# FARMER FUNCTIONS
# ========================================

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
    """Register a farmer on the blockchain."""
    farmer_input = (
        farmer_id,
        nic,
        full_name,
        home_address,
        district,
        contact_number,
        total_paddy_area,
    )

    value = web3_accounts.to_wei(value_eth, 'ether')

    try:
        user_accounts_contract.functions.registerFarmer(farmer_input).call({
            'from': WALLET_ADDRESS,
            'value': value
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = user_accounts_contract.functions.registerFarmer(farmer_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_accounts.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_accounts.to_wei('20', 'gwei'),
        'value': value
    })

    signed_tx = web3_accounts.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_accounts.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())

    receipt = web3_accounts.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_farmer(farmer_id: str):
    """View a farmer by ID."""
    try:
        farmer = user_accounts_contract.functions.getFarmer(farmer_id).call()
        print("\n--- Farmer Data ---")
        print("ID:", farmer[0])
        print("NIC:", farmer[1])
        print("Full Name:", farmer[2])
        print("Address:", farmer[3])
        print("District:", farmer[4])
        print("Contact:", farmer[5])
        print("Total Paddy Field Area:", farmer[6])
        return farmer
    except Exception as e:
        print("Error fetching farmer:", e)
        return None


def view_all_farmers():
    """View all registered farmers."""
    try:
        farmers = user_accounts_contract.functions.getAllFarmers().call()
        print("\n--- All Registered Farmers ---")
        for f in farmers:
            print("\nID:", f[0])
            print("NIC:", f[1])
            print("Full Name:", f[2])
            print("Address:", f[3])
            print("District:", f[4])
            print("Contact:", f[5])
            print("Total Paddy Field Area:", f[6])
        return farmers
    except Exception as e:
        print("Error fetching farmers:", e)
        return []


# ========================================
# COLLECTOR FUNCTIONS
# ========================================

def add_collector(
    collector_id: str,
    nic: str,
    full_name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register a collector on the blockchain."""
    collector_input = (
        collector_id,
        nic,
        full_name,
        home_address,
        district,
        contact_number,
    )

    value = web3_accounts.to_wei(value_eth, 'ether')

    try:
        user_accounts_contract.functions.registerCollector(collector_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = user_accounts_contract.functions.registerCollector(collector_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_accounts.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_accounts.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_accounts.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_accounts.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_accounts.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_collector(collector_id: str):
    """View a collector by ID."""
    try:
        collector = user_accounts_contract.functions.getCollector(collector_id).call()
        print("\n--- Collector Data ---")
        print("ID:", collector[0])
        print("NIC:", collector[1])
        print("Full Name:", collector[2])
        print("Address:", collector[3])
        print("District:", collector[4])
        print("Contact:", collector[5])
        return collector
    except Exception as e:
        print("Error fetching collector:", e)
        return None


def view_all_collectors():
    """View all registered collectors."""
    try:
        collectors = user_accounts_contract.functions.getAllCollectors().call()
        print("\n--- All Registered Collectors ---")
        for c in collectors:
            print("\nID:", c[0])
            print("NIC:", c[1])
            print("Full Name:", c[2])
            print("Address:", c[3])
            print("District:", c[4])
            print("Contact:", c[5])
        return collectors
    except Exception as e:
        print("Error fetching collectors:", e)
        return []


# ========================================
# MILLER FUNCTIONS
# ========================================

def add_miller(
    miller_id: str,
    company_register_number: str,
    company_name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register a miller on the blockchain."""
    miller_input = (
        miller_id,
        company_register_number,
        company_name,
        home_address,
        district,
        contact_number,
    )

    value = web3_accounts.to_wei(value_eth, 'ether')

    try:
        user_accounts_contract.functions.registerMiller(miller_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = user_accounts_contract.functions.registerMiller(miller_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_accounts.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_accounts.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_accounts.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_accounts.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_accounts.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_miller(miller_id: str):
    """View a miller by ID."""
    try:
        miller = user_accounts_contract.functions.getMiller(miller_id).call()
        print("\n--- Miller Data ---")
        print("ID:", miller[0])
        print("Company Register Number:", miller[1])
        print("Company Name:", miller[2])
        print("Address:", miller[3])
        print("District:", miller[4])
        print("Contact:", miller[5])
        return miller
    except Exception as e:
        print("Error fetching miller:", e)
        return None


def view_all_millers():
    """View all registered millers."""
    try:
        millers = user_accounts_contract.functions.getAllMillers().call()
        print("\n--- All Registered Millers ---")
        for m in millers:
            print("\nID:", m[0])
            print("Company Register Number:", m[1])
            print("Company Name:", m[2])
            print("Address:", m[3])
            print("District:", m[4])
            print("Contact:", m[5])
        return millers
    except Exception as e:
        print("Error fetching millers:", e)
        return []


# ========================================
# WHOLESALER FUNCTIONS
# ========================================

def add_wholesaler(
    wholesaler_id: str,
    company_register_number: str,
    company_name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register a wholesaler on the blockchain."""
    wholesaler_input = (
        wholesaler_id,
        company_register_number,
        company_name,
        home_address,
        district,
        contact_number,
    )

    value = web3_accounts.to_wei(value_eth, 'ether')

    try:
        user_accounts_contract.functions.registerWholesaler(wholesaler_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = user_accounts_contract.functions.registerWholesaler(wholesaler_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_accounts.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_accounts.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_accounts.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_accounts.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_accounts.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_all_wholesalers():
    """View all registered wholesalers."""
    try:
        wholesalers = user_accounts_contract.functions.getAllWholesalers().call()
        print("\n--- All Registered Wholesalers ---")
        for w in wholesalers:
            print("\nID:", w[0])
            print("Company Register Number:", w[1])
            print("Company Name:", w[2])
            print("Address:", w[3])
            print("District:", w[4])
            print("Contact:", w[5])
        return wholesalers
    except Exception as e:
        print("Error fetching wholesalers:", e)
        return []


# ========================================
# RETAILER FUNCTIONS
# ========================================

def add_retailer(
    retailer_id: str,
    name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register a retailer on the blockchain."""
    retailer_input = (
        retailer_id,
        name,
        home_address,
        district,
        contact_number,
    )

    value = web3_accounts.to_wei(value_eth, 'ether')

    try:
        user_accounts_contract.functions.registerRetailer(retailer_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = user_accounts_contract.functions.registerRetailer(retailer_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_accounts.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_accounts.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_accounts.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_accounts.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_accounts.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_all_retailers():
    """View all registered retailers."""
    try:
        retailers = user_accounts_contract.functions.getAllRetailers().call()
        print("\n--- All Registered Retailers ---")
        for r in retailers:
            print("\nID:", r[0])
            print("Name:", r[1])
            print("Address:", r[2])
            print("District:", r[3])
            print("Contact:", r[4])
        return retailers
    except Exception as e:
        print("Error fetching retailers:", e)
        return []


# ========================================
# BREWER (BEER) FUNCTIONS
# ========================================

def add_brewer(
    brewer_id: str,
    company_id: str,
    name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register a brewer on the blockchain."""
    brewer_input = (
        brewer_id,
        company_id,
        name,
        home_address,
        district,
        contact_number,
    )

    value = web3_accounts.to_wei(value_eth, 'ether')

    try:
        user_accounts_contract.functions.registerBrewer(brewer_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = user_accounts_contract.functions.registerBrewer(brewer_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_accounts.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_accounts.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_accounts.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_accounts.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_accounts.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_all_brewers():
    """View all registered brewers."""
    try:
        brewers = user_accounts_contract.functions.getAllBrewers().call()
        print("\n--- All Registered Brewers ---")
        for b in brewers:
            print("\nID:", b[0])
            print("Company ID:", b[1])
            print("Name:", b[2])
            print("Address:", b[3])
            print("District:", b[4])
            print("Contact:", b[5])
        return brewers
    except Exception as e:
        print("Error fetching brewers:", e)
        return []


# ========================================
# ANIMAL FOOD FUNCTIONS
# ========================================

def add_animal_food(
    animal_food_id: str,
    company_id: str,
    name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register an animal food company on the blockchain."""
    animal_food_input = (
        animal_food_id,
        company_id,
        name,
        home_address,
        district,
        contact_number,
    )

    value = web3_accounts.to_wei(value_eth, 'ether')

    try:
        user_accounts_contract.functions.registerAnimalFood(animal_food_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = user_accounts_contract.functions.registerAnimalFood(animal_food_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_accounts.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_accounts.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_accounts.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_accounts.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_accounts.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_all_animal_foods():
    """View all registered animal food companies."""
    try:
        animal_foods = user_accounts_contract.functions.getAllAnimalFoods().call()
        print("\n--- All Registered Animal Food Companies ---")
        for a in animal_foods:
            print("\nID:", a[0])
            print("Company ID:", a[1])
            print("Name:", a[2])
            print("Address:", a[3])
            print("District:", a[4])
            print("Contact:", a[5])
        return animal_foods
    except Exception as e:
        print("Error fetching animal foods:", e)
        return []


# ========================================
# EXPORTER FUNCTIONS
# ========================================

def add_exporter(
    exporter_id: str,
    company_id: str,
    name: str,
    home_address: str,
    district: str,
    contact_number: str,
    value_eth: float = 0.0,
):
    """Register an exporter on the blockchain."""
    exporter_input = (
        exporter_id,
        company_id,
        name,
        home_address,
        district,
        contact_number,
    )

    value = web3_accounts.to_wei(value_eth, 'ether')

    try:
        user_accounts_contract.functions.registerExporter(exporter_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = user_accounts_contract.functions.registerExporter(exporter_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_accounts.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_accounts.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_accounts.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_accounts.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_accounts.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_all_exporters():
    """View all registered exporters."""
    try:
        exporters = user_accounts_contract.functions.getAllExporters().call()
        print("\n--- All Registered Exporters ---")
        for e in exporters:
            print("\nID:", e[0])
            print("Company ID:", e[1])
            print("Name:", e[2])
            print("Address:", e[3])
            print("District:", e[4])
            print("Contact:", e[5])
        return exporters
    except Exception as e:
        print("Error fetching exporters:", e)
        return []


# ========================================
# TRANSACTION FUNCTIONS
# ========================================

def record_transaction(
    from_party: str,
    to_party: str,
    product_type: str,
    quantity: int,
    value_eth: float = 0.0,
):
    """Record a transaction on the blockchain."""
    value = web3_operations.to_wei(value_eth, 'ether')

    try:
        operations_contract.functions.recordTransaction(
            from_party,
            to_party,
            product_type,
            quantity
        ).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = operations_contract.functions.recordTransaction(
        from_party,
        to_party,
        product_type,
        quantity
    ).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_operations.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_operations.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_operations.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_operations.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_operations.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_all_transactions():
    """View all recorded transactions."""
    try:
        transactions = operations_contract.functions.getAllTransactions().call()
        print("\n--- All Recorded Transactions ---")
        for tx in transactions:
            print("\nFrom:", tx[0])
            print("To:", tx[1])
            print("Product Type:", tx[2])
            print("Quantity:", tx[3])
            print("Timestamp:", tx[4])
        return transactions
    except Exception as e:
        print("Error fetching transactions:", e)
        return []


# ========================================
# DAMAGE RECORD FUNCTIONS
# ========================================

def record_damage(
    user_id: str,
    paddy_type: str,
    quantity: int,
    damage_date: int,
    value_eth: float = 0.0,
):
    """Record damage on the blockchain."""
    damage_input = (
        user_id,
        paddy_type,
        quantity,
        damage_date,
    )

    value = web3_operations.to_wei(value_eth, 'ether')

    try:
        operations_contract.functions.recordDamage(damage_input).call({
            'from': WALLET_ADDRESS,
            'value': value,
        })
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = operations_contract.functions.recordDamage(damage_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_operations.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_operations.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_operations.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_operations.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_operations.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_all_damage_records():
    """View all damage records."""
    try:
        damage_records = operations_contract.functions.getAllDamageRecords().call()
        print("\n--- All Damage Records ---")
        for dr in damage_records:
            print("\nUser ID:", dr[0])
            print("Paddy Type:", dr[1])
            print("Quantity:", dr[2])
            print("Damage Date:", dr[3])
        return damage_records
    except Exception as e:
        print("Error fetching damage records:", e)
        return []


def record_milling(miller_id, paddy_type, input_qty, output_qty, date):
    """Record milling operation on the blockchain and return the block hash."""
    print("\n--- Recording Milling on Blockchain ---")
    print(f"Miller ID: {miller_id}")
    print(f"Paddy Type: {paddy_type}")
    print(f"Input Qty: {input_qty}")
    print(f"Output Qty: {output_qty}")
    print(f"Date: {date}")

    # Create milling input tuple
    milling_input = (miller_id, paddy_type, input_qty, output_qty, date)
    value = 0  # No ETH value sent

    # Test call
    try:
        operations_contract.functions.recordMilling(milling_input).call({'from': WALLET_ADDRESS, 'value': value})
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = operations_contract.functions.recordMilling(milling_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_operations.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_operations.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_operations.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_operations.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_operations.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def view_all_milling_records():
    """View all milling records."""
    try:
        milling_records = operations_contract.functions.getAllMillingRecords().call()
        print("\n--- All Milling Records ---")
        for mr in milling_records:
            print("\nMiller ID:", mr[0])
            print("Paddy Type:", mr[1])
            print("Input Qty:", mr[2])
            print("Output Qty:", mr[3])
            print("Date:", mr[4])
        return milling_records
    except Exception as e:
        print("Error fetching milling records:", e)
        return []


def record_rice_transaction(from_party, to_party, rice_type, quantity, price=0.0):
    """Record a rice transaction on the blockchain and return the block hash."""
    print("\n--- Recording Rice Transaction on Blockchain ---")
    print(f"From: {from_party}")
    print(f"To: {to_party}")
    print(f"Rice Type: {rice_type}")
    print(f"Quantity: {quantity}")
    print(f"Price: {price}")

    qty = int(quantity)
    value = 0  # No ETH value sent

    # Test call
    try:
        operations_contract.functions.recordRiceTransaction(from_party, to_party, rice_type, qty).call({'from': WALLET_ADDRESS, 'value': value})
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = operations_contract.functions.recordRiceTransaction(from_party, to_party, rice_type, qty).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_operations.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_operations.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_operations.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_operations.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_operations.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


def record_rice_damage(user_id, rice_type, quantity, damage_date):
    """Record rice damage on the blockchain and return the block hash."""
    print("\n--- Recording Rice Damage on Blockchain ---")
    print(f"User ID: {user_id}")
    print(f"Rice Type: {rice_type}")
    print(f"Quantity: {quantity}")
    print(f"Damage Date: {damage_date}")

    # Create rice damage input tuple
    rice_damage_input = (user_id, rice_type, int(quantity), int(damage_date))
    value = 0  # No ETH value sent

    # Test call
    try:
        operations_contract.functions.recordRiceDamage(rice_damage_input).call({'from': WALLET_ADDRESS, 'value': value})
        print("Call simulation succeeded (no revert).")
    except Exception as e:
        print("Call simulation reverted or failed:", e)
        return None

    tx = operations_contract.functions.recordRiceDamage(rice_damage_input).build_transaction({
        'from': WALLET_ADDRESS,
        'nonce': web3_operations.eth.get_transaction_count(WALLET_ADDRESS),
        'gas': 2000000,
        'gasPrice': web3_operations.to_wei('20', 'gwei'),
        'value': value,
    })

    signed_tx = web3_operations.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3_operations.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("Transaction sent:", tx_hash.hex())
    receipt = web3_operations.eth.wait_for_transaction_receipt(tx_hash)
    print("Transaction mined! Block number:", receipt.blockNumber)
    print("Transaction mined! Block hash:", receipt.blockHash.hex())
    return receipt.blockHash.hex()


# ========================================
# UTILITY FUNCTIONS
# ========================================

def check_connection():
    """Check if web3 is connected to the blockchain."""
    if web3.is_connected():
        print("✓ Connected to blockchain")
        print("Network ID:", web3_operations.eth.chain_id)
        print("Latest block:", web3_operations.eth.block_number)
        return True
    else:
        print("✗ Not connected to blockchain")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Rice Supply Chain Blockchain Interface")
    print("=" * 50)
    check_connection()
