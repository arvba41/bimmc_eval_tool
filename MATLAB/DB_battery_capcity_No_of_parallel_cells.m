function [BatteryCapacity_per_submodule,NoofParallel_cells] = DB_battery_capcity_No_of_parallel_cells(Ebatt,Uc_n,DoD,NoofCells_mtx,NoofSM_total_mtx,Bcap)
% Function to calculate the total battery capacity per submodule and also
% calculate the total number of parallel cells per submodule
%
% [BatteryCapacity_per_submodule,NoofParallel_cells] = DB_battery_capcity_No_of_parallel_cells(Ebatt,Uc_n,DoD,NoofCells_mtx,NoofSM_total_mtx,Bcap)
% 
% Ebatt --> Total battery capacity in Wh
% Uc_n --> Nominal cell voltage
% DoD --> Depth of discharge
% NoofCells_mtx --> Number of cascaded cells per submodule vector
% NoofSM_total_mtx --> Total number of submodules
% Bcap --> Capacity of a single cell in Ah

% battery capacity per submodule
BatteryCapacity_per_submodule = Ebatt./...
    (Uc_n*DoD.*NoofCells_mtx.*NoofSM_total_mtx);
% number of parallel cells per submodule
NoofParallel_cells = BatteryCapacity_per_submodule/Bcap;  