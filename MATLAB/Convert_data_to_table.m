% Loading datat from DashBoard
% load Dashboard_data.mat

% %% Initialixing topology list
Data_row_init = strcat(Topologies_Name,'-',num2str(NoofCells(1)),...
    '_N_scells-',num2str(NoofPhases_Names(1)));
% Data_column = squeeze(NoofSM_total_mtx(:,1,1)); 
Data_row_tab_init = Data_row_init;
% 
% %% Initializing variables
% NoofSM_tot_tab = squeeze(NoofSM_total_mtx(:,1,1)); % number of submodules initial vlaue

%% 2-level inverter losses calculation
% Change the following code if somthing in the App database is changed.
% ...
% ...
%% CAB450M12XM3 https://www.wolfspeed.com/downloads/dl/file/id/1493/product/482/cab450m12xm3.pdf
% MOSFET ordered by Scania
    Rdson_2l_avg_Wolfspeed = 2.6e-3; % on-state resistance average typical
    Rdson_2l_max_Wolfspeed = 4.6e-3; % on-state resistance maximum typical
    Tj_max_2l_Wolfspeed = 175; % maximum MOSFET junction temperature

    Rthata_jc_Wolfspeed = 0.13; % junction to case thermal resistance [K/W]
    Rthata_ca_Wolfspeed = 0.03; % case to ambient thermal resistance [K/W] % adapted from the other MOSFET

    E_on_datasheet_avg_Wolfspeed = 11e-3; % turn-on energy for 2-level inverter average
    E_off_datasheet_avg_Wolfspeed = 10.1e-3; % turn-on energy for 2-level inverter average

    E_on_datasheet_max_Wolfspeed = 13e-3; % turn-on energy for 2-level inverter maximum
    E_off_datasheet_max_Wolfspeed = 12.1e-3; % turn-on energy for 2-level inverter maximum

    k_sc_Wolfspeed = 590; % cost per module [€/Module] https://www.mouser.se/ProductDetail/Wolfspeed-Cree/CAB400M12XM3?qs=%2Fha2pyFadui2zI2EBZMgPnH0VO%2F63kquGbk4HsSV4qnvSIzMb5Lbvw==&utm_source=octopart&utm_medium=aggregator&utm_campaign=941-CAB400M12XM3&utm_content=Cree%2C+Inc.
    k_GateDrive_Wolfspeed = 2*238; % Gate drive cost per module [2x€/Module] https://www.mouser.se/ProductDetail/Wolfspeed-Cree/CGD1700HB2M-UNA?qs=%2Fha2pyFaduhKT5mPQri3tTWDGO%252Be%2FRbChE85nHFaBEA%3D
    k_controller_Wolfspeed = 100; % Controller, sensor, saftey costs [€/converter] Arbitrary guess

    P_sw_loss_avg_Wolfspeed = 2*(E_on_datasheet_avg_Wolfspeed + E_off_datasheet_avg_Wolfspeed)*Params.p2l*f; % converter switching losses average per phase
    P_sw_loss_max_Wolfspeed = 2*(E_on_datasheet_max_Wolfspeed + E_off_datasheet_max_Wolfspeed)*Params.p2l*f; % converter switching losses maximum per phase

    dTja_Wolfspeed = Tj_max_2l_Wolfspeed - Params.Ta2l; % case to ambient temperature rise

    Npmos_2l_Wolfspeed = Io_max^2*Rdson_2l_max_Wolfspeed*(Rthata_jc_Wolfspeed + Rthata_ca_Wolfspeed)./(dTja_Wolfspeed - P_sw_loss_max_Wolfspeed.*(Rthata_jc_Wolfspeed + Rthata_ca_Wolfspeed)); % number of parallel MOSFETs

    Npmos_2l_active_Wolfspeed = max(1,Npmos_2l_Wolfspeed); % minimum number of parallel MOSFETs is 1
    %                 NoofParallel_MOSFETs_2l = 2*I_sw_max_sw_mtx.^2.*RdsonMax_mtx.*Rthata_ca./...
    %                 (2*dTca - Noofswitches_per_sm_mtx.*Params.Rca.*U_s_mtx.*I_sw_av_max_sw_mtx.*t_sw_max_mtx.*Params.p*f); % number of parallel cells matrix; % number of parallel MOSFETs

    P_con_loss_avg_Wolfspeed = Io_avg^2*Rdson_2l_avg_Wolfspeed/Npmos_2l_active_Wolfspeed; % conduction losses average

    P_con_loss_max_Wolfspeed = Io_max^2*Rdson_2l_max_Wolfspeed/Npmos_2l_active_Wolfspeed; % conduction losses maximum

    P_2l_loss_avg_Wolfspeed = 3*(P_con_loss_avg_Wolfspeed + P_sw_loss_avg_Wolfspeed); % converter losses (2-level inverter) average
    P_2l_loss_max_Wolfspeed = 3*(P_con_loss_max_Wolfspeed + P_sw_loss_max_Wolfspeed); % converter losses (2-level inverter) maximum

    Tj_2l_avg_Wolfspeed = (Rthata_jc_Wolfspeed + Rthata_ca_Wolfspeed).*(P_con_loss_avg_Wolfspeed + P_sw_loss_avg_Wolfspeed) + Params.Ta2l; % Rth*losses per MOSFET
    Tj_2l_max_Wolfspeed = (Rthata_jc_Wolfspeed + Rthata_ca_Wolfspeed).*(P_con_loss_max_Wolfspeed + P_sw_loss_max_Wolfspeed) + Params.Ta2l; % Rth*losses per MOSFET

    lambda_sc_2l_Wolfspeed = k_sc_Wolfspeed.*Npmos_2l_active_Wolfspeed.*3; % cost of semiconductors
    lambda_sm_2l_Wolfspeed = k_GateDrive_Wolfspeed.*3.*2 + k_controller_Wolfspeed ; % sigle gate ddriver for all parallel Modules

    lambda_conv_2l_Wolfspeed = lambda_sc_2l_Wolfspeed + lambda_sm_2l_Wolfspeed; % total converter cost [€]
% ...
%% MOSFET parameters SKM260MB170SCH17 https://www.semikron.com/products/product-classes/sic/full-sic.html?gclid=Cj0KCQjw1PSDBhDbARIsAPeTqrfZFFtmi-OvJA3cEEd_GSzI6kiJcClEeWGpl3p7jE_XqF-Hw37RNVIaArYNEALw_wcB#view/table/items/20/order/id-in-a+desc/
    Rdson_2l_avg_semikron = 10e-3; % on-state resistance average 
    Rdson_2l_max_semikron = 15e-3; % on-state resistance maximum

    Rthata_jc_semikron = 0.065; % junction to case thermal resistance [K/W]
    Rthata_ca_semikron = 0.03; % case to ambient thermal resistance [K/W]
    % For this loss calculations the body diode losses are
    % neglected as they are in conduction only during the
    % dead-time intervals 

    Tj_max_2l_semikron = 175; % maximum MOSFET junction temperature

    E_on_datasheet_max_semikron = 7.59e-3; % turn-on energy for 2-level inverter maximum
    E_off_datasheet_max_semikron = 6.21e-3; % turn-on energy for 2-level inverter maximum

    E_on_datasheet_avg_semikron = 5.1e-3; % turn-on energy for 2-level inverter average
    E_off_datasheet_avg_semikron = 2.5e-3; % turn-on energy for 2-level inverter average

    % Assumed same value as the previous FET
    k_sc_semikron = 590; % cost per module [€/Module] https://www.mouser.se/ProductDetail/Wolfspeed-Cree/CAB400M12XM3?qs=%2Fha2pyFadui2zI2EBZMgPnH0VO%2F63kquGbk4HsSV4qnvSIzMb5Lbvw==&utm_source=octopart&utm_medium=aggregator&utm_campaign=941-CAB400M12XM3&utm_content=Cree%2C+Inc.
    k_GateDrive_semikron = 2*238; % Gate drive cost per module [2x€/Module] https://www.mouser.se/ProductDetail/Wolfspeed-Cree/CGD1700HB2M-UNA?qs=%2Fha2pyFaduhKT5mPQri3tTWDGO%252Be%2FRbChE85nHFaBEA%3D
    k_controller_semikron = 100; % Controller, sensor, saftey costs [€/converter] Arbitrary guess

    P_sw_loss_avg_semikron = (E_on_datasheet_avg_semikron + E_off_datasheet_avg_semikron)*Params.p2l*f; % converter switching losses average
    P_sw_loss_max_semikron = (E_on_datasheet_max_semikron + E_off_datasheet_max_semikron)*Params.p2l*f; % converter switching losses maximum

    dTja_semikron = Tj_max_2l_semikron - Params.Ta2l; % case to ambient temperature rise

    Npmos_2l_semikron = Io_max^2*Rdson_2l_max_semikron*(Rthata_jc_semikron + Rthata_ca_semikron)./(dTja_semikron - P_sw_loss_max_semikron.*(Rthata_jc_semikron + Rthata_ca_semikron)); % number of parallel MOSFETs

    Npmos_2l_active_semikron = max(1,Npmos_2l_semikron); % minimum number of parallel MOSFETs is 1

    P_con_loss_avg_semikron = Io_avg^2*Rdson_2l_avg_semikron/Npmos_2l_semikron; % conduction losses average
    P_con_loss_max_semikron = Io_max^2*Rdson_2l_max_semikron/Npmos_2l_semikron; % conduction losses maximum

    P_2l_loss_avg_semikron = 3*(P_con_loss_avg_semikron + P_sw_loss_avg_semikron); % converter losses (2-level inverter) average
    P_2l_loss_max_semikron = 3*(P_con_loss_max_semikron + P_sw_loss_max_semikron); % converter losses (2-level inverter) maximum

    Tj_2l_avg_semikron = (Rthata_jc_semikron + Rthata_ca_semikron).*(P_con_loss_avg_semikron + P_sw_loss_avg_semikron) + Params.Ta2l; % Rth*losses per MOSFET pair
    Tj_2l_max_semikron = (Rthata_jc_semikron + Rthata_ca_semikron).*(P_con_loss_max_semikron + P_sw_loss_max_semikron) + Params.Ta2l; % Rth*losses per MOSFET pair

    lambda_sc_2l_semikron = k_sc_semikron.*Npmos_2l_active_semikron.*3; % cost of semiconductors
    lambda_sm_2l_semikron = k_GateDrive_semikron.*3.*2 + k_controller_semikron ; % sigle gate ddriver for all parallel Modules

    lambda_conv_2l_semikron = lambda_sc_2l_semikron + lambda_sm_2l_semikron; % total converter cost [€] 
    
%% Topology name series (Row elements)
% Annoying 'for' loops
% for j = 1:length(NoofPhases)% outer loop for phases runthough
%     for i = 1:length(NoofCells) % inner loop for cell runthrough
%         % Topology names
%         Data_row_prev = Data_row_tab_init;
%         Data_row_elements = strcat(Topologies_Name,'-',...
%             num2str(NoofCells(i)),'_N_scells-',...
%             NoofPhases_Names(j));
%         Data_row_tab_init = cat(1,Data_row_prev,Data_row_elements);
%     end
% end 
% Data_row_tab_init(1,:) = []; % neglect the initial row
% Data_row = Data_row_tab_init(:); % data row matrix

[Topologies_NameList_mtx,Noofcells_str_mtx,NoofPhases_str_mtx] = ...
    ndgrid(Topologies_Name,NoofCells_Name,NoofPhases_NamesList); 
    % Topologies names, number of cells, number of phases string vector

Data_row_mtx = strcat(Topologies_NameList_mtx,'_',Noofcells_str_mtx,...
    '_',NoofPhases_str_mtx); % concatination of topology names string

Data_row = Data_row_mtx(:); 

Topologies_NameList_list = Topologies_NameList_mtx(:);
Noofcells_str_list = Noofcells_str_mtx(:);
NoofPhases_str_list = NoofPhases_str_mtx(:);

%% Evalulation parameters 
% number of submodules, battery capacity and number of parallel cells
% per submodule 
NoofSubmodules_tot_tab = NoofSM_total_mtx(:); % number of submodules
% NoofSubmodules_tot_tab(end+2) = 0;
Bcap_tot_tab = BatteryCapacity_per_submodule(:); % battery capacity per submodule [Ah]
% Bcap_tot_tab(end+2) = 0;
NoofParallel_mosfets_tab = NoofParallel_actiVe_mosfets_mtx(:); % Number of parallel cells per submodule
% battery losses 
Pbatt_avg_tab = Pbatt_avg_tot_mtx(:); % Average battery power losses [W]
Pbatt_max_tab = Pbatt_max_tot_mtx(:); % Maximum battery power losses [W]
% capactior losses
Pcap_avg_tab = Pcap_avg_tot_mtx(:); % Avereage capacitor losses [W]
Pcap_max_tab = Pcap_max_tot_mtx(:); % Maximum capacitor losse [W]
% Semiconductor losse
Psc_tot_avg_tab = Psc_tot_avg_mtx(:); % semiconductor losses average [W]
Psc_tot_max_tab = Psc_tot_max_mtx(:); % semiconductor losses maximum [W]
% Case temperatures
Tc_avg_tab = Tc_avg_mtx(:); % average case temperatude [degC]
Tc_max_tab = Tc_max_mtx(:); % maximum case temperatude [degC]
% total losses
Ploss_tot_avg_tab = Ploss_tot_avg_mtx(:); % total average losses [W]
Ploss_tot_max_tab = Ploss_tot_max_mtx(:); % total maximum losses [W]
% efficiencices
eff_tot_avg_tab = eff_tot_avg_mtx(:); % total efficiency average 
eff_tot_max_tab = eff_tot_max_mtx(:); % total efficiency maximum
% Costs
lambda_MOSFET_tab = lambda_MOSFET_mtx(:); % semiconductor costs 
lambda_SubmoduleCost_tab = lambda_SubmoduleCost_mtx(:); % fixed cost per submodule
lambda_CapCost_tab = lambda_CapCost_mtx(:); % capacitor cost
lambda_BatteryCost_tab = lambda_BatteryCost_mtx(:); % battery cost

Column_vector_label = {'Topologies','Topology Names','Number of cells'...
    'Number of phases','Number_of_submoules',...
    'Battery_capacity_per_submodule','Number_of_parallel_MOSFETs',...
    'Average_battery_losses','Maximum_battery_losses',...
    'Average_capacitor_losses','Maximum_capacitor_losses',...
    'Average_converter_losses','Maximum_converter_losses',...
    'Average_case_temperature','Maximum_case_temperature',...
    'Average_total_losses','Maximum_total_losses',...
    'Average_total_efficiency','Maximum_total_efficiency',...
    'Total_semiconductor_costs','Total_submodule_costs',...
    'Total_capacitor_costs','Total_battery_costs'};

Dashboard_array = [Data_row Topologies_NameList_list Noofcells_str_list...
    NoofPhases_str_list NoofSubmodules_tot_tab Bcap_tot_tab ...
    NoofParallel_mosfets_tab Pbatt_avg_tab Pbatt_max_tab ...
    Pcap_avg_tab Pcap_max_tab Psc_tot_avg_tab Psc_tot_max_tab ...
    Tc_avg_tab Tc_max_tab Ploss_tot_avg_tab Ploss_tot_max_tab ...
    eff_tot_avg_tab eff_tot_max_tab lambda_MOSFET_tab ...
    lambda_SubmoduleCost_tab lambda_CapCost_tab lambda_BatteryCost_tab];

Dashboard_table = array2table(Dashboard_array,'VariableNames'...
    ,Column_vector_label,'RowNames',Data_row);

Dashboard_row_end = "2L_inv";

P_2l_tot_loss_avg = Pbatt_2l_avg+Pcap_2l_avg+P_2l_loss_avg; % Average total losses 2-level inverter
P_2l_tot_loss_max = Pbatt_2l_max+Pcap_2l_max+P_2l_loss_max; % Maixmum total losses 2-level inverter

eff_tot_2l_avg = Params.Pout./(Params.Pout + P_2l_tot_loss_avg); % Average efficiency 2-level inverter
eff_tot_2l_max = Params.Pout*Params.ocf./(Params.Pout*Params.ocf + P_2l_tot_loss_max); % Maximum efficiency 2-level inverter

Dashboard_table(end+1,:) = array2table([Dashboard_row_end 0 0 3 0 0 Npmos_2l ...
    Pbatt_2l_avg Pbatt_2l_max Pcap_2l_avg Pcap_2l_max P_2l_loss_avg ...
    P_2l_loss_max 0 0 P_2l_tot_loss_avg P_2l_tot_loss_max ...
    eff_tot_2l_avg eff_tot_2l_max lambda_MOSFET_2l lambda_sm_2l ...
    Params.Kcap.*Ecap_2l Params.Kbatt.*Params.Ebatt]);

writetable(Dashboard_table,'Dasboard_raw_data.xlsx')      

% 
% Data_row(end+1) = "2L_inv_Wolfspeed"; % 2-level inverter Wolfspeed
% Data_row(end+1) = "2L_inv_Semikron"; % 2-level inverter Semikron