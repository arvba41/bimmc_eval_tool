function [Cap_C_mtx,Cap_ESR_mtx,Cap_Ipk_mtx,Cap_Pmax_unit,NcapC_mtx,Acap_mtx,Zeta_mmc_mtx] = DB_capacitor_calc(Params,NoofSM_total_mtx,U_s_sw_mtx,x_param,NoofCells_mtx,NoofParallel_cells,Topologies,NoofCells,NoofPhases)
% Function to calculate the MMC submodule DC-link capacitor parameters 
%
% [Cap_C_mtx,Cap_ESR_mtx,Cap_Ipk_mtx,Cap_Pmax_unit,NcapC_mtx,Acap_mtx,Zeta_mmc_mtx] = DB_capacitor_calc(Params,NoofSM_total_mtx,U_s_sw_mtx,x_param,NoofCells_mtx,NoofParallel_cells,Topologies,NoofCells,NoofPhases)
% 
% Cap_C_mtx --> Capacitance per submodule vector
% Cap_ESR_mtx --> Capacitor equivalent series resistance vector
% Cap_Ipk_mtx --> Capacitor peak current vector
% Cap_Ppk_mtx --> Capacitor peak power vector
% NcapC_mtx --> Number of parellel capacitors  
% Acap_mtx --> Area of capacitor vector 
% Zeta_mmc_mtx --> Damping ratio vector 
% 
% Params --> input parameter structure
% NoofSM_total_mtx --> Total number of submodules vector
% U_s_sw_mtx --> Dc-side submodule voltage vector 
% Zeta_2l --> 2-level inverter damping factor 
% x_param --> Cell inductance 
% NoofCells_mtx --> Number of cascaded cells per submodule vector 
% NoofParallel_cells --> Number of parallel cells per submodule 
% Topologies --> Topology vector
% NoofCells --> number of cells vector
% NoofPhases --> Number of phases vector
% number of cascaded cells per submodule 



% capacitor losses
if Params.EnESRCal 
    % Comment the following line when using the optimizer
    load Eparam.mat % load matric for optimized calues of Energies
    Cap_C_mtx = Eparam.*2./(NoofSM_total_mtx.*U_s_sw_mtx.^2);
%     Cap_ESR_mtx = 2*Zeta_2l.*sqrt((Params.Lbatt_leads + x_param(9)*NoofCells_mtx./NoofParallel_cells)./Cap_C_mtx); % calculating based on the constant xeta as that of the 2-level inverter
else
%     Cap_ESR_mtx = Params.Cap_SM_ESR*ones(size(I_arm_max_mtx)); % old calculations considering on the input parameters
%     Cap_ESR_mtx = Params.Cap_SM_ESR/100./(2*pi*1000*Cap_C_mtx); % old calculations considering on the input parameters
    Cap_C_mtx = Params.Ecap_SM_tot*2./(NoofSM_total_mtx.*U_s_sw_mtx.^2);
end

if Params.OptimEnable % Enable optimized results 
    if Params.Reoptimize
        load('OptimVars_new.mat', 'Optimal_Ecap_vector') 
        Ecap_mtx = Optimal_Ecap_vector;
    else
        load('OptimVars.mat', 'Optimal_Ecap_vector')
        Ecap_mtx = Optimal_Ecap_vector(Topologies,NoofCells,NoofPhases);
    end
    load OptimVars.mat % load optimal variables
    Cap_C_mtx = Ecap_mtx.*2./(NoofSM_total_mtx.*U_s_sw_mtx.^2);
end

[dummy,Cap_C_unit_mtx,dummy] = ndgrid(Topologies,Params.Ccap_unit(NoofCells),NoofPhases);
[dummy,Cap_ESR_unit_mtx,dummy] = ndgrid(Topologies,Params.ESR_unit(NoofCells),NoofPhases);
[dummy,Cap_Ipk_unit_mtx,dummy] = ndgrid(Topologies,Params.Icap_unit(NoofCells),NoofPhases);
[dummy,Cap_A_unit_mtx,dummy] = ndgrid(Topologies,Params.Acap_unit(NoofCells),NoofPhases);
Cap_Pmax_unit = Cap_ESR_unit_mtx.*Cap_Ipk_unit_mtx.^2;

NcapC_mtx = Cap_C_mtx./Cap_C_unit_mtx;
%             NcapE_mtx = 0.5*Cap_C_mtx.*U_s_sw_mtx.^2./Ecap_pk;
Cap_ESR_mtx = Cap_ESR_unit_mtx./NcapC_mtx;
Cap_Ipk_mtx = Cap_Ipk_unit_mtx.*ones(size(NcapC_mtx));
Acap_mtx  = NcapC_mtx.*Cap_A_unit_mtx;

% Cap_Ipk_mtx = Params.Icap_pk_single_cell*log_rate_mtx;
% Ecap_pk=min(Params.Ecap_max_cell,Params.Ecap_single_cell*NoofCells_mtx);
% Cap_DF_mtx = Params.Cap_SM_DF/100*log_rate_mtx;
% Cap_ESR_mtx = Cap_DF_mtx./(2*pi*1000*Cap_C_mtx); % old calculations considering on the input parameters

Zeta_mmc_mtx = 0.5*Cap_ESR_mtx.*sqrt(Cap_C_mtx./(Params.Lpcb + Params.Lbatt_leads + x_param(9).*NoofCells_mtx./NoofParallel_cells));