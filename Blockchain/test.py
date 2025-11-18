from interacter import add_farmer, add_miller, add_collector, record_transaction, view_all_transactions, view_transaction

# Simple test that calls add_farmer with dummy values.
# Make sure your local node and contract are running/deployed before running this.

if __name__ == "__main__":
    print("Calling add_farmer with dummy values...")
    try:
        add_farmer(
            "test03",
            "000000000V",
            "Test Farmer",
            "123 Test Street",
            "TestDistrict",
            "0770000000",
            1,
            0.0,
        )
        print("add_farmer call finished.")
        print("Calling add_miller with dummy values...")
        add_miller(
            "miller01",
            "CRN123456",
            "Test Miller Co",
            "456 Mill Road",
            "MillDistrict",
            "0771111111",
            0.0,
        )
        print("add_miller call finished.")
        print("Calling add_collector with dummy values...")
        add_collector(
            "collector01",
            "COLNIC123",
            "Test Collector",
            "789 Collect Lane",
            "CollectDistrict",
            "0772222222",
            0.0,
        )
        print("add_collector call finished.")
        print("Recording a sample transaction from farmer test03 to miller miller01...")
        try:
            record_transaction("test03", "miller01", "Paddy", 100)
            print("record_transaction call finished.")
        except Exception as e:
            print("record_transaction raised an exception:", e)

        print("Viewing all transactions (may fall back to events)...")
        try:
            view_all_transactions(0)
        except Exception as e:
            print("view_all_transactions raised an exception:", e)

        print("Viewing transaction with ID 1...")
        try:
            view_transaction(1)
        except Exception as e:
            print("view_transaction raised an exception:", e)
    except Exception as e:
        print("add_farmer raised an exception:", e)
