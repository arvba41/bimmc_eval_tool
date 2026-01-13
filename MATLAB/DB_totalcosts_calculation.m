function [lambda_MOSFET_mtx,lambda_SubmoduleCost_mtx,lambda_TotalConverterCost_mtx,lambda_CapCost_mtx,lambda_BatteryCost_mtx,lambda_converter_normalized,lambda_TotalCost_mtx,lambda_TotalCost_2l_mtx,lambda_TotalCost_normalized] = DB_totalcosts_calculation(Params,k_sc_mtx,NoofParallel_actiVe_mosfets_mtx,Noofswitches_per_sm_mtx,NoofSM_total_mtx,NcapC_mtx,NoofCells_mtx,lambda_conv_2l_mtx)
% Function to calculate the total cost of the converter
% 
% [lambda_MOSFET_mtx,lambda_SubmoduleCost_mtx,lambda_TotalConverterCost_mtx,lambda_CapCost_mtx,lambda_BatteryCost_mtx,lambda_converter_normalized,lambda_TotalCost_mtx,lambda_TotalCost_2l_mtx,lambda_TotalCost_normalized] = DB_totalcosts_calculation(Params,k_sc_mtx,NoofParallel_actiVe_mosfets_mtx,Noofswitches_per_sm_mtx,NoofSM_total_mtx,E_cap_tot_mtx,NoofCells_mtx,lambda_conv_2l_mtx)

lambda_MOSFET_mtx = k_sc_mtx.*NoofParallel_actiVe_mosfets_mtx.*Noofswitches_per_sm_mtx.*NoofSM_total_mtx; % total cost of MOSFETs for MMC vewctor
lambda_SubmoduleCost_mtx = Params.ksm.*NoofSM_total_mtx; % total fized cost per submodule vector
lambda_converter_mtx = cat(4,lambda_MOSFET_mtx,lambda_SubmoduleCost_mtx); % total cost of the converter

% lambda_CapCost_mtx = Params.Kcap.*E_cap_tot_mtx; % total cost of the energy storage elements vector
lambda_CapCost_mtx = Params.Kcap.*NcapC_mtx.*NoofSM_total_mtx; % total cost of the energy storage elements vector

lambda_BatteryCost_mtx = Params.Kbatt.*Params.Ebatt.*ones(size(NoofCells_mtx)); % total cost of the battery vector

lambda_TotalConverterCost_mtx = cat(4,lambda_converter_mtx,lambda_CapCost_mtx); % total cost vector
lambda_converter_normalized = lambda_TotalConverterCost_mtx./lambda_conv_2l_mtx; % normalized coneverter costs

lambda_TotalCost_mtx = cat(4,lambda_BatteryCost_mtx,lambda_converter_mtx,lambda_CapCost_mtx); % total cost vector

lambda_TotalCost_2l_mtx =  lambda_BatteryCost_mtx + lambda_conv_2l_mtx; % total cost of 2-level inverter vecotr

lambda_TotalCost_normalized = lambda_TotalCost_mtx./lambda_TotalCost_2l_mtx; % normalized coneverter costs