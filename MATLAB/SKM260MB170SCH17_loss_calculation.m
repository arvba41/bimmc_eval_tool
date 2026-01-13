%% MOSFET parameters SKM260MB170SCH17 https://www.semikron.com/products/product-classes/sic/full-sic.html?gclid=Cj0KCQjw1PSDBhDbARIsAPeTqrfZFFtmi-OvJA3cEEd_GSzI6kiJcClEeWGpl3p7jE_XqF-Hw37RNVIaArYNEALw_wcB#view/table/items/20/order/id-in-a+desc/

Rdson_2l_avg_SemiTrans = 10e-3; % on-state resistance average typical
    Rdson_2l_max_SemiTrans = 14e-3; % on-state resistance maximum typical
    Tj_max_2l_SemiTrans = 175; % maximum MOSFET junction temperature

    Rthata_jc_SemiTrans = 0.056; % junction to case thermal resistance [K/W]
    k_sc_SemiTrans = 590; % cost per module [€/Module] https://www.mouser.se/ProductDetail/Wolfspeed-Cree/CAB400M12XM3?qs=%2Fha2pyFadui2zI2EBZMgPnH0VO%2F63kquGbk4HsSV4qnvSIzMb5Lbvw==&utm_source=octopart&utm_medium=aggregator&utm_campaign=941-CAB400M12XM3&utm_content=Cree%2C+Inc.
    k_GateDrive_SemiTrans = 2*238; % Gate drive cost per module [2x€/Module] https://www.mouser.se/ProductDetail/Wolfspeed-Cree/CGD1700HB2M-UNA?qs=%2Fha2pyFaduhKT5mPQri3tTWDGO%252Be%2FRbChE85nHFaBEA%3D
    k_controller_SemiTrans = 100; % Controller, sensor, saftey costs [€/converter] Arbitrary guess
        
    % Rise and fall times for the switching transients using The MOSFET
    % datasheet 
    E_sw_datasheet_avg_SemiTrans = 4e-3+2e-3+1.8e-3; % total energy loses during switching for 900 V DC link at 150degC and Rg as 1.1 Ohm (ajusting for the temperature setting from the graph in datasheet)
    E_sw_datasheet_max_SemiTrans = 17e-3+17e-3+3.6e-3; % total energy loses during switching for 900 V DC link for 150degC and Rg as 1.1 Ohm 
    
    t_sw_2l_avg = 2*E_sw_datasheet_avg_SemiTrans/(0.5*Params.Udc*I_2l_abs_avg*Params.p2l*f); % switching transient time 2-level inverter average
    t_sw_2l_max = 2*E_sw_datasheet_max_SemiTrans/(0.5*Params.Udc*I_2l_abs_avg_max*Params.p2l*f); % switching transient time 2-level inverter maximum
    
    dTja = Tj_max_2l_SemiTrans - Params.Ta2l; % junction to ambient temperature difference [degC]
        
    A_mos_2l = 53e-3*80e-3; % 2-level inverter area [m^2] from datasheet
    
    % We know that dTca = N_sw*N_pmos*Pmos*Rthata_ca
    % Pmos is calculated using the following
%     Pmos_2l_max_dummy = I_2l_rms_max.^2.*Rdson_2l_max_SemiTrans + ...
%         0.5*Params.Udc.*I_2l_abs_avg_max.*t_sw_2l_max.*Params.p2l*f; 

    Npmos_2l_active_SemiTrans = 1; % minimum number of parallel MOSFETs
    
    % MOSFET conduction losses 
    P_con_loss_mos_avg_SemiTrans = I_2l_rms_avg.^2.*Rdson_2l_avg_SemiTrans./Npmos_2l_active_SemiTrans.^2; % Average 
    P_con_loss_mos_max_SemiTrans = I_2l_rms_max.^2.*Rdson_2l_max_SemiTrans./Npmos_2l_active_SemiTrans.^2; % Maximum
    % MOSFET Switching losses losses 
    P_sw_loss_mos_avg_SemiTrans = 0.5*Params.Udc.*I_2l_abs_avg.*t_sw_2l_avg.*Params.p2l*f./Npmos_2l_active_SemiTrans; % Average
    P_sw_loss_mos_max_SemiTrans = 0.5*Params.Udc.*I_2l_abs_avg_max.*t_sw_2l_max.*Params.p2l*f./Npmos_2l_active_SemiTrans; % Maximum
    % Total MOSFET losses
    P_mos_loss_mos_avg_SemiTrans = P_con_loss_mos_avg_SemiTrans + P_sw_loss_mos_avg_SemiTrans; % average
    P_mos_loss_mos_max_SemiTrans = P_con_loss_mos_max_SemiTrans + P_sw_loss_mos_max_SemiTrans; % maximum

    % total semiconductor losses
    P_2l_loss_avg_SemiTrans = 3*2*(P_mos_loss_mos_avg_SemiTrans).*Npmos_2l_active_SemiTrans; % average
    P_2l_loss_max_SemiTrans = 3*2*(P_mos_loss_mos_max_SemiTrans).*Npmos_2l_active_SemiTrans; % maximum
    
    % Calculating the case to ambient thermal resistance considering two
    % modules
    Rtheta_ca_2l = (dTja - P_mos_loss_mos_max_SemiTrans.*Rthata_jc_SemiTrans)...
        ./(2*P_mos_loss_mos_max_SemiTrans.*Npmos_2l_active_SemiTrans);
        
    % calculating the heat transfer coefficient for 2-level inverter
    Htfr_2l =1./(Rtheta_ca_2l.*A_mos_2l);

    
    % Case temperature 
    Tc_2l_avg_SemiTrans = 2*P_mos_loss_mos_avg_SemiTrans*Rtheta_ca_2l + Params.Ta2l; % average
    Tc_2l_max_SemiTrans = 2*P_mos_loss_mos_max_SemiTrans*Rtheta_ca_2l + Params.Ta2l; % maximum
    % junction temperatures
    Tj_2l_avg_SemiTrans = P_mos_loss_mos_avg_SemiTrans.*Rthata_jc_SemiTrans + Tc_2l_avg_SemiTrans; % average
    Tj_2l_max_SemiTrans = P_mos_loss_mos_max_SemiTrans.*Rthata_jc_SemiTrans + Tc_2l_max_SemiTrans; % maximum
    
    lambda_sc_2l_SemiTrans = k_sc_SemiTrans.*Npmos_2l_active_SemiTrans.*3; % cost of semiconductors
    lambda_sm_2l_SemiTrans = k_GateDrive_SemiTrans.*3.*2 + k_controller_SemiTrans ; % sigle gate ddriver for all parallel Modules

    lambda_conv_2l_SemiTrans = lambda_sc_2l_SemiTrans + lambda_sm_2l_SemiTrans; % total converter cost [€]
% ...
% ...
% Converting to the dashboard specific data
    P_2l_loss_avg = P_2l_loss_avg_SemiTrans;
    P_2l_loss_max = P_2l_loss_max_SemiTrans;
    
    Tj_2l_avg = Tj_2l_avg_SemiTrans; % average junction temperature
    Tj_2l_max = Tj_2l_max_SemiTrans; % maximum junction temperature
    
    Tc_2l_avg = Tc_2l_avg_SemiTrans; % average case temperature
    Tc_2l_max = Tc_2l_max_SemiTrans; % maximum case temperature
    
    lambda_MOSFET_2l = lambda_sc_2l_SemiTrans; % 2-levl inverter MOSFET cost 
    lambda_sm_2l = lambda_sm_2l_SemiTrans; % 2-level inverter submodule fixed costs 
    lambda_conv_2l = lambda_conv_2l_SemiTrans; % total converter cost
       
    Npmos_2l = Npmos_2l_active_SemiTrans; % number of parlalel MOSFETs