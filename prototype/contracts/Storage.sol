// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Storage {
    // --- Farmer structure ---
    struct Farmer {
        string id; // Government-issued ID
        string nic;
        string fullName;
        string homeAddress;
        string district;
        string contactNumber;
        uint256 totalPaddyFieldArea;
    }

    // --- Collector structure ---
    struct Collector {
        string id;
        string nic;
        string fullName;
        string homeAddress;
        string district;
        string contactNumber;
    }

    // --- Miller structure ---
    struct Miller {
        string id;
        string companyRegisterNumber;
        string companyName;
        string homeAddress;
        string district;
        string contactNumber;
    }

    // --- Input structs for registration ---
    struct FarmerInput {
        string id;
        string nic;
        string fullName;
        string homeAddress;
        string district;
        string contactNumber;
        uint256 totalPaddyFieldArea;
    }

    struct CollectorInput {
        string id;
        string nic;
        string fullName;
        string homeAddress;
        string district;
        string contactNumber;
    }

    struct MillerInput {
        string id;
        string companyRegisterNumber;
        string companyName;
        string homeAddress;
        string district;
        string contactNumber;
    }

    // --- Storage mappings ---
    mapping(string => Farmer) public farmers;
    mapping(string => Collector) public collectors;
    mapping(string => Miller) public millers;
    // Keep a list of registered farmer IDs so we can enumerate farmers
    string[] public farmerIds;
    // Keep a list of registered miller IDs so we can enumerate millers
    string[] public millerIds;
    // Keep a list of registered collector IDs so we can enumerate collectors
    string[] public collectorIds;

    // --- Events ---
    event FarmerRegistered(string id, string fullName);
    event CollectorRegistered(string id, string fullName);
    event MillerRegistered(string id, string companyName);

    // --- Register Farmer ---
    function registerFarmer(FarmerInput calldata input) external {
        require(bytes(farmers[input.id].id).length == 0, "Farmer already registered");

        farmers[input.id] = Farmer({
            id: input.id,
            nic: input.nic,
            fullName: input.fullName,
            homeAddress: input.homeAddress,
            district: input.district,
            contactNumber: input.contactNumber,
            totalPaddyFieldArea: input.totalPaddyFieldArea
        });

        // track id for enumeration
        farmerIds.push(input.id);

        emit FarmerRegistered(input.id, input.fullName);
    }

    // --- Register Collector ---
    function registerCollector(CollectorInput calldata input) external {
        require(bytes(collectors[input.id].id).length == 0, "Collector already registered");

        collectors[input.id] = Collector({
            id: input.id,
            nic: input.nic,
            fullName: input.fullName,
            homeAddress: input.homeAddress,
            district: input.district,
            contactNumber: input.contactNumber
        });

        // track id for enumeration
        collectorIds.push(input.id);

        emit CollectorRegistered(input.id, input.fullName);
    }

    // --- Register Miller ---
    function registerMiller(MillerInput calldata input) external {
        require(bytes(millers[input.id].id).length == 0, "Miller already registered");

        millers[input.id] = Miller({
            id: input.id,
            companyRegisterNumber: input.companyRegisterNumber,
            companyName: input.companyName,
            homeAddress: input.homeAddress,
            district: input.district,
            contactNumber: input.contactNumber
        });

        // track id for enumeration
        millerIds.push(input.id);

        emit MillerRegistered(input.id, input.companyName);
    }

    // --- View functions ---
    function getFarmer(string calldata _id) external view returns (Farmer memory) {
        require(bytes(farmers[_id].id).length != 0, "Farmer not found");
        return farmers[_id];
    }

    function getCollector(string calldata _id) external view returns (Collector memory) {
        require(bytes(collectors[_id].id).length != 0, "Collector not found");
        return collectors[_id];
    }

    function getMiller(string calldata _id) external view returns (Miller memory) {
        require(bytes(millers[_id].id).length != 0, "Miller not found");
        return millers[_id];
    }

    // Return all registered farmer IDs
    function getFarmerIds() external view returns (string[] memory) {
        return farmerIds;
    }

    // Return all registered farmers
    function getAllFarmers() external view returns (Farmer[] memory) {
        uint256 len = farmerIds.length;
        Farmer[] memory list = new Farmer[](len);
        for (uint256 i = 0; i < len; i++) {
            list[i] = farmers[farmerIds[i]];
        }
        return list;
    }

    // Return all registered miller IDs
    function getMillerIds() external view returns (string[] memory) {
        return millerIds;
    }

    // Return all registered collector IDs
    function getCollectorIds() external view returns (string[] memory) {
        return collectorIds;
    }

    // Return all registered collectors
    function getAllCollectors() external view returns (Collector[] memory) {
        uint256 len = collectorIds.length;
        Collector[] memory list = new Collector[](len);
        for (uint256 i = 0; i < len; i++) {
            list[i] = collectors[collectorIds[i]];
        }
        return list;
    }

    // Return all registered millers
    function getAllMillers() external view returns (Miller[] memory) {
        uint256 len = millerIds.length;
        Miller[] memory list = new Miller[](len);
        for (uint256 i = 0; i < len; i++) {
            list[i] = millers[millerIds[i]];
        }
        return list;
    }
}
