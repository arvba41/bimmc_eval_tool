%% CAB450M12XM3 https://www.wolfspeed.com/downloads/dl/file/id/1493/product/482/cab450m12xm3.pdf
% MOSFET ordered by Scania
    Rdson_2l_avg_Wolfspeed = 2.6e-3; % on-state resistance average typical
    Rdson_2l_max_Wolfspeed = 4.6e-3; % on-state resistance maximum typical
    Tj_max_2l_Wolfspeed = 175; % maximum MOSFET junction temperature

    Rthata_jc_Wolfspeed = 0.13; % junction to case thermal resistance [K/W]
    k_sc_Wolfspeed = 590; % cost per module [€/Module] https://www.mouser.se/ProductDetail/Wolfspeed-Cree/CAB400M12XM3?qs=%2Fha2pyFadui2zI2EBZMgPnH0VO%2F63kquGbk4HsSV4qnvSIzMb5Lbvw==&utm_source=octopart&utm_medium=aggregator&utm_campaign=941-CAB400M12XM3&utm_content=Cree%2C+Inc.
    k_GateDrive_Wolfspeed = 2.*238; % Gate drive cost per module [2x€/Module] https://www.mouser.se/ProductDetail/Wolfspeed-Cree/CGD1700HB2M-UNA?qs=%2Fha2pyFaduhKT5mPQri3tTWDGO%252Be%2FRbChE85nHFaBEA%3D
    k_controller_Wolfspeed = 100; % Controller, sensor, saftey costs [€/converter] Arbitrary guess
        
    % Rise and fall times for the switching transients using The MOSFET
    % datasheet 
    E_sw_datasheet_avg_Wolfspeed = 7e-3; % total energy loses during switching for 800 V DC link
    E_sw_datasheet_max_Wolfspeed = 40e-3; % total energy loses during switching for 800 V DC link 35mJ for 25degC
    
    t_sw_2l_avg = 2*E_sw_datasheet_avg_Wolfspeed/(Params.Udc*I_2l_abs_avg); % switching transient time 2-level inverter average
    t_sw_2l_max = 2.*E_sw_datasheet_max_Wolfspeed./(Params.Udc.*I_2l_abs_avg_max); % switching transient time 2-level inverter maximum
    
    dTja = Tj_max_2l_Wolfspeed - Params.Ta2l; % junction to ambient temperature difference [degC]
        
    A_mos_2l = 53e-3*80e-3; % 2-level inverter area [m^2] from datasheet
    
    % We know that dTca = N_sw*N_pmos*Pmos*Rthata_ca
    % Pmos is calculated using the following
%     Pmos_2l_max_dummy = I_2l_rms_max.^2.*Rdson_2l_max_Wolfspeed + ...
%         0.5*Params.Udc.*I_2l_abs_avg_max.*t_sw_2l_max.*Params.p2l*f; 

    Npmos_2l_active_Wolfspeed = 2; % minimum number of parallel MOSFETs
    
    % MOSFET conduction losses 
    P_con_loss_mos_avg_Wolfspeed = I_2l_rms_avg.^2.*Rdson_2l_avg_Wolfspeed./Npmos_2l_active_Wolfspeed.^2; % Average 
    P_con_loss_mos_max_Wolfspeed = I_2l_rms_max.^2.*Rdson_2l_max_Wolfspeed./Npmos_2l_active_Wolfspeed.^2; % Maximum
    % MOSFET Switching losses losses 
    P_sw_loss_mos_avg_Wolfspeed = Params.Udc.*I_2l_abs_avg.*t_sw_2l_avg.*Params.p2l*f./Npmos_2l_active_Wolfspeed; % Average
    P_sw_loss_mos_max_Wolfspeed = Params.Udc.*I_2l_abs_avg_max.*t_sw_2l_max.*Params.p2l*f./Npmos_2l_active_Wolfspeed; % Maximum
    % Total MOSFET losses
    P_mos_loss_mos_avg_Wolfspeed = P_con_loss_mos_avg_Wolfspeed + P_sw_loss_mos_avg_Wolfspeed; % average
    P_mos_loss_mos_max_Wolfspeed = P_con_loss_mos_max_Wolfspeed + P_sw_loss_mos_max_Wolfspeed; % maximum

    % total semiconductor losses
    P_2l_loss_avg_Wolfspeed = 3*2*(P_mos_loss_mos_avg_Wolfspeed).*Npmos_2l_active_Wolfspeed; % average
    P_2l_loss_max_Wolfspeed = 3*2*(P_mos_loss_mos_max_Wolfspeed).*Npmos_2l_active_Wolfspeed; % maximum
    
    % Calculating the case to ambient thermal resistance considering two
    % modules
    Rtheta_ca_2l = (dTja - P_mos_loss_mos_max_Wolfspeed.*Rthata_jc_Wolfspeed)...
        ./(2*P_mos_loss_mos_max_Wolfspeed.*Npmos_2l_active_Wolfspeed);
        
    % calculating the heat transfer coefficient for 2-level inverter
    Htfr_2l =1./(Rtheta_ca_2l.*A_mos_2l);

    
    % Case temperature 
    Tc_2l_avg_Wolfspeed = 2.*P_mos_loss_mos_avg_Wolfspeed.*Rtheta_ca_2l + Params.Ta2l; % average
    Tc_2l_max_Wolfspeed = 2.*P_mos_loss_mos_max_Wolfspeed.*Rtheta_ca_2l + Params.Ta2l; % maximum
    % junction temperatures
    Tj_2l_avg_Wolfspeed = P_mos_loss_mos_avg_Wolfspeed.*Rthata_jc_Wolfspeed + Tc_2l_avg_Wolfspeed; % average
    Tj_2l_max_Wolfspeed = P_mos_loss_mos_max_Wolfspeed.*Rthata_jc_Wolfspeed + Tc_2l_max_Wolfspeed; % maximum
    
    lambda_sc_2l_Wolfspeed = k_sc_Wolfspeed.*Npmos_2l_active_Wolfspeed.*3; % cost of semiconductors
    lambda_sm_2l_Wolfspeed = k_GateDrive_Wolfspeed.*3.*2 + k_controller_Wolfspeed ; % sigle gate ddriver for all parallel Modules

    lambda_conv_2l_Wolfspeed = lambda_sc_2l_Wolfspeed + lambda_sm_2l_Wolfspeed; % total converter cost [€]
% ...
% ...
% Converting to the dashboard specific data
    P_2l_loss_avg = P_2l_loss_avg_Wolfspeed;
    P_2l_loss_max = P_2l_loss_max_Wolfspeed;
    
    Tj_2l_avg = Tj_2l_avg_Wolfspeed; % average junction temperature
    Tj_2l_max = Tj_2l_max_Wolfspeed; % maximum junction temperature
    
    Tc_2l_avg = Tc_2l_avg_Wolfspeed; % average case temperature
    Tc_2l_max = Tc_2l_max_Wolfspeed; % maximum case temperature
    
    lambda_MOSFET_2l = lambda_sc_2l_Wolfspeed; % 2-levl inverter MOSFET cost 
    lambda_sm_2l = lambda_sm_2l_Wolfspeed; % 2-level inverter submodule fixed costs 
    lambda_conv_2l = lambda_conv_2l_Wolfspeed; % total converter cost
       
    Npmos_2l = Npmos_2l_active_Wolfspeed; % number of parlalel MOSFETs