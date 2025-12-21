// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Operations {
    // --- Damage record structure ---
    struct DamageRecord { 
        string userId;
        string paddyType;
        uint256 quantity;
        uint256 damageDate;
    }

    // --- Transaction structure ---
    struct Transaction {
        string fromParty;
        string toParty;
        string productType;
        uint256 quantity;
        uint256 timestamp;
    }

    // --- Rice Damage record structure ---
    struct RiceDamageRecord { 
        string userId;
        string riceType;
        uint256 quantity;
        uint256 damageDate;
    }

    // --- Rice Transaction structure ---
    struct RiceTransaction {
        string fromParty;
        string toParty;
        string riceType;
        uint256 quantity;
        uint256 timestamp;
    }

    // --- Milling record structure ---
    struct MillingRecord {
        string millerId;
        string paddyType;
        uint256 inputQty;
        uint256 outputQty;
        uint256 date;
    }

    // --- Input structs ---
    struct DamageRecordInput {
        string userId;
        string paddyType;
        uint256 quantity;
        uint256 damageDate;
    }

    struct RiceDamageRecordInput {
        string userId;
        string riceType;
        uint256 quantity;
        uint256 damageDate;
    }

    struct MillingRecordInput {
        string millerId;
        string paddyType;
        uint256 inputQty;
        uint256 outputQty;
        uint256 date;
    }

    // --- Damage records ---
    uint256 public nextDamageId;
    mapping(uint256 => DamageRecord) public damageRecords;

    // --- Transaction tracking ---
    uint256 public nextTxId;
    mapping(uint256 => Transaction) public transactions; // txId -> Transaction

    // Optional indexes for traceability per actor
    mapping(string => uint256[]) public sentTxs;    // sender name -> txIds
    mapping(string => uint256[]) public receivedTxs; // receiver name -> txIds

    // --- Rice Damage records ---
    uint256 public nextRiceDamageId;
    mapping(uint256 => RiceDamageRecord) public riceDamageRecords;

    // --- Rice Transaction tracking ---
    uint256 public nextRiceTxId;
    mapping(uint256 => RiceTransaction) public riceTransactions; // txId -> RiceTransaction

    // Optional indexes for traceability per actor for rice
    mapping(string => uint256[]) public sentRiceTxs;    // sender name -> txIds
    mapping(string => uint256[]) public receivedRiceTxs; // receiver name -> txIds

    // --- Milling records ---
    uint256 public nextMillingId;
    mapping(uint256 => MillingRecord) public millingRecords;

    // --- Events ---
    event DamageRecorded(
        uint256 indexed damageId,
        string userId,
        string paddyType,
        uint256 quantity,
        uint256 damageDate
    );
    
    // Log for off-chain traceability
    event TransactionRecorded(
        uint256 indexed txId,
        string indexed fromParty,
        string indexed toParty,
        string productType,
        uint256 quantity,
        uint256 timestamp
    );

    event RiceDamageRecorded(
        uint256 indexed damageId,
        string userId,
        string riceType,
        uint256 quantity,
        uint256 damageDate
    );

    event RiceTransactionRecorded(
        uint256 indexed txId,
        string indexed fromParty,
        string indexed toParty,
        string riceType,
        uint256 quantity,
        uint256 timestamp
    );

    event MillingRecorded(
        uint256 indexed millingId,
        string millerId,
        string paddyType,
        uint256 inputQty,
        uint256 outputQty,
        uint256 date
    );

    // --- Transaction recording ---
    function recordTransaction(
        string calldata fromParty,
        string calldata toParty,
        string calldata productType,
        uint256 quantity
    ) external {
        uint256 txId = nextTxId;
        // initialize nextTxId if zero (start at 1)
        if (txId == 0) {
            txId = 1;
            nextTxId = 2;
        } else {
            nextTxId = txId + 1;
        }

        transactions[txId] = Transaction({
            fromParty: fromParty,
            toParty: toParty,
            productType: productType,
            quantity: quantity,
            timestamp: block.timestamp
        });

        sentTxs[fromParty].push(txId);
        receivedTxs[toParty].push(txId);

        emit TransactionRecorded(txId, fromParty, toParty, productType, quantity, block.timestamp);
    }

    // Return single transaction by id
    function getTransaction(uint256 txId) external view returns (Transaction memory) {
        require(txId != 0 && txId < nextTxId, "Transaction not found");
        return transactions[txId];
    }

    // Return all transactions (for small datasets)
    function getAllTransactions() external view returns (Transaction[] memory) {
        uint256 len = nextTxId == 0 ? 0 : nextTxId - 1;
        Transaction[] memory list = new Transaction[](len);
        for (uint256 i = 0; i < len; i++) {
            list[i] = transactions[i + 1];
        }
        return list;
    }

    // --- Record Damage ---
    function recordDamage(DamageRecordInput calldata input) external {
        uint256 damageId = nextDamageId;
        if (damageId == 0) {
            damageId = 1;
            nextDamageId = 2;
        } else {
            nextDamageId = damageId + 1;
        }

        damageRecords[damageId] = DamageRecord({
            userId: input.userId,
            paddyType: input.paddyType,
            quantity: input.quantity,
            damageDate: input.damageDate
        });

        emit DamageRecorded(
            damageId,
            input.userId,
            input.paddyType,
            input.quantity,
            input.damageDate
        );
    }

    // Get damage record
    function getDamageRecord(uint256 _damageId) external view returns (DamageRecord memory) {
        require(_damageId != 0 && _damageId < nextDamageId, "Damage record not found");
        return damageRecords[_damageId];
    }

    // Return all damage records
    function getAllDamageRecords() external view returns (DamageRecord[] memory) {
        uint256 len = nextDamageId == 0 ? 0 : nextDamageId - 1;
        DamageRecord[] memory list = new DamageRecord[](len);
        for (uint256 i = 0; i < len; i++) {
            list[i] = damageRecords[i + 1];
        }
        return list;
    }

    // --- Rice Transaction recording ---
    function recordRiceTransaction(
        string calldata fromParty,
        string calldata toParty,
        string calldata riceType,
        uint256 quantity
    ) external {
        uint256 txId = nextRiceTxId;
        // initialize nextRiceTxId if zero (start at 1)
        if (txId == 0) {
            txId = 1;
            nextRiceTxId = 2;
        } else {
            nextRiceTxId = txId + 1;
        }

        riceTransactions[txId] = RiceTransaction({
            fromParty: fromParty,
            toParty: toParty,
            riceType: riceType,
            quantity: quantity,
            timestamp: block.timestamp
        });

        sentRiceTxs[fromParty].push(txId);
        receivedRiceTxs[toParty].push(txId);

        emit RiceTransactionRecorded(txId, fromParty, toParty, riceType, quantity, block.timestamp);
    }

    // Return single rice transaction by id
    function getRiceTransaction(uint256 txId) external view returns (RiceTransaction memory) {
        require(txId != 0 && txId < nextRiceTxId, "Rice transaction not found");
        return riceTransactions[txId];
    }

    // Return all rice transactions (for small datasets)
    function getAllRiceTransactions() external view returns (RiceTransaction[] memory) {
        uint256 len = nextRiceTxId == 0 ? 0 : nextRiceTxId - 1;
        RiceTransaction[] memory list = new RiceTransaction[](len);
        for (uint256 i = 0; i < len; i++) {
            list[i] = riceTransactions[i + 1];
        }
        return list;
    }

    // --- Record Rice Damage ---
    function recordRiceDamage(RiceDamageRecordInput calldata input) external {
        uint256 damageId = nextRiceDamageId;
        if (damageId == 0) {
            damageId = 1;
            nextRiceDamageId = 2;
        } else {
            nextRiceDamageId = damageId + 1;
        }

        riceDamageRecords[damageId] = RiceDamageRecord({
            userId: input.userId,
            riceType: input.riceType,
            quantity: input.quantity,
            damageDate: input.damageDate
        });

        emit RiceDamageRecorded(
            damageId,
            input.userId,
            input.riceType,
            input.quantity,
            input.damageDate
        );
    }

    // Get single rice damage record
    function getRiceDamageRecord(uint256 _damageId) external view returns (RiceDamageRecord memory) {
        require(_damageId != 0 && _damageId < nextRiceDamageId, "Rice damage record not found");
        return riceDamageRecords[_damageId];
    }

    // Return all rice damage records
    function getAllRiceDamageRecords() external view returns (RiceDamageRecord[] memory) {
        uint256 len = nextRiceDamageId == 0 ? 0 : nextRiceDamageId - 1;
        RiceDamageRecord[] memory list = new RiceDamageRecord[](len);
        for (uint256 i = 0; i < len; i++) {
            list[i] = riceDamageRecords[i + 1];
        }
        return list;
    }

    // --- Record Milling ---
    function recordMilling(MillingRecordInput calldata input) external {
        uint256 millingId = nextMillingId;
        if (millingId == 0) {
            millingId = 1;
            nextMillingId = 2;
        } else {
            nextMillingId = millingId + 1;
        }

        millingRecords[millingId] = MillingRecord({
            millerId: input.millerId,
            paddyType: input.paddyType,
            inputQty: input.inputQty,
            outputQty: input.outputQty,
            date: input.date
        });

        emit MillingRecorded(
            millingId,
            input.millerId,
            input.paddyType,
            input.inputQty,
            input.outputQty,
            input.date
        );
    }

    // Get single milling record
    function getMillingRecord(uint256 _millingId) external view returns (MillingRecord memory) {
        require(_millingId != 0 && _millingId < nextMillingId, "Milling record not found");
        return millingRecords[_millingId];
    }

    // Return all milling records
    function getAllMillingRecords() external view returns (MillingRecord[] memory) {
        uint256 len = nextMillingId == 0 ? 0 : nextMillingId - 1;
        MillingRecord[] memory list = new MillingRecord[](len);
        for (uint256 i = 0; i < len; i++) {
            list[i] = millingRecords[i + 1];
        }
        return list;
    }
}
