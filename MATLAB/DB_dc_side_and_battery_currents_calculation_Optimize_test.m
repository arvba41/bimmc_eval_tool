function [Z_batt_mtx,Z_cap_mtx,E_cap_tot_mtx,Ibatt_avg_mtx,Ibatt_max_mtx,Icap_avg_mtx,Icap_max_mtx] = DB_dc_side_and_battery_currents_calculation_Optimize_test(Params,t,idc_avg_t_mtx,idc_max_t_mtx,Topologies,NoofCells,NoofPhases,NoofParallel_cells,Cap_ESR_mtx,Cap_C_mtx,U_s_sw_mtx,NoofSM_total_mtx)
% Function to calculate the DC-side, battery, and capacitor currents
% 
% [Z_batt_mtx,Z_cap_mtx,E_cap_tot_mtx,Ibatt_avg_mtx,Ibatt_max_mtx,Icap_avg_mtx,Icap_max_mtx] = DB_dc_side_and_battery_currents_calculation(Params,t,idc_avg_t_mtx,idc_max_t_mtx,Topologies,NoofCells,NoofPhases,NoofParallel_cells,Cap_ESR_mtx,Cap_C_mtx,U_s_sw_mtx,NoofSM_total_mtx)

global Ecap_vector_sweep p_vector_sweep

% DC Side submodule current
Idc_avg_t_mtx = FFT_function_3d(idc_avg_t_mtx(:,:,2:end),t); % Average DC side current Frequency response
[Idc_max_t_mtx,F] = FFT_function_3d(idc_max_t_mtx(:,:,2:end),t); % Maximum DC side current Frequency response

[~,~,F_mtx] = ndgrid(Ecap_vector_sweep,p_vector_sweep,F); % frequency vector
% [~,NoofCells_F_mtx,~,~] = ndgrid(Topologies,NoofCells,NoofPhases,F); % number of cells time vectors
% Battery impedance
s = 1j*2*pi*F_mtx;

% Battery cell impedance function with RL
% Z_cell_fn_RL = @(x)(x(1) ... % R0
%     + x(2)./(s*x(2)*x(3)+1) + ... % R1||C1
%     x(4)./(s*x(4)*x(5)+1) + x(6)./(s*x(6)*x(7)+1) + ... % R2||C2 + R3||C3
%     s*x(8)*x(9)./(x(8) + s*x(9))); ... % Rs||Ls
% 
% Battery cell impedance function with L only
% Z_cell_fn_L = @(x)(x(1) ... % R0
%     + x(2)./(s*x(2)*x(3)+1) + ... % R1||C1
%     x(4)./(s*x(4)*x(5)+1) + x(6)./(s*x(6)*x(7)+1) + ... % R2||C2 + R3||C3
%     s*x(8)); ... % |Ls
% 
% loading the paramters file from Scania battery EIS extraction
% load SS1_25C_1_param.mat
% load SS1_25C_1_param2.mat
% 
% Load Samsung 24Ah cell EIS
% name='PHEV2_24A_New_25m';
% 
% eval(['load ',name,'.txt']);
% eval(['lokal=',name]);
% 
% [NumberOfMeasurementpoints,dummy]=size(lokal);
% 
% StartSelection=1;
% EndSelection=NumberOfMeasurementpoints;
% 
% f_vect=lokal(StartSelection:EndSelection,3);
% z_real=lokal(StartSelection:EndSelection,4);
% z_imag=lokal(StartSelection:EndSelection,5);
% z_vect=z_real+sqrt(-1)*z_imag;

if Params.AlelionEnable % Enable Alelion cell EIS data
    % Load Samsung 24Ah cell EIS
    name='PHEV2_24A_New_25m';

    eval(['load ',name,'.txt']);
    eval(['lokal=',name]);

    [NumberOfMeasurementpoints,dummy]=size(lokal);

    StartSelection=1;
    EndSelection=NumberOfMeasurementpoints;

    f_vect=lokal(StartSelection:EndSelection,3);
    z_real=lokal(StartSelection:EndSelection,4);
    z_imag=lokal(StartSelection:EndSelection,5);
    
    Z_cell_real=interp1(f_vect,z_real,F_mtx,'linear','extrap');
    Z_cell_imag=interp1(f_vect,z_imag,F_mtx,'linear','extrap');
    Z_cell=Z_cell_real+1j*Z_cell_imag;

    Z_cell_real_dc=interp1(f_vect,z_real,ones(size(F_mtx(:,:,1)))*Params.DC_imp_freq,'linear','extrap');
    Z_cell_imag_dc=interp1(f_vect,z_imag,ones(size(F_mtx(:,:,1)))*Params.DC_imp_freq,'linear','extrap');
    Z_cell(:,:,1)=Z_cell_real_dc+1j*Z_cell_imag_dc; % DC cell impedance

    x_param(9) = 50e-9;
else
    load SS1_25C_1_param_nominal.mat 
    %                 Battery cell impedance function with RL
    Z_cell_fn_RL = @(x)(x(1) ... % R0
        + x(2)./(s*x(2)*x(3)+1) + ... % R1||C1
        x(4)./(s*x(4)*x(5)+1) + x(6)./(s*x(6)*x(7)+1) + ... % R2||C2 + R3||C3
        s*x(8)*x(9)./(x(8) + s*x(9))); ... % Rs||Ls

    Z_cell = Z_cell_fn_RL(x_param); % impedance of the cell using R/L
%     Z_cell = Z_cell_fn_L(x_param2); % impedance of the cell using L only
%     Z_cell(:,:,:,1) = x(1) + x(2) + x(4) + x(6) ; % DC battery impedance (analytically MATLAB gives 'Inf')

end
% Capacitor impedance
% This is a lame code with a FOR loop :-(
% for i = 1:length(F)
%     NoofParallel_cells_F_mtx(:,:,:,i) = NoofParallel_cells;
% end
Z_batt_mtx = s*Params.Lbatt_leads + Z_cell.*NoofCells./NoofParallel_cells; % battery impednace vector

% Cap_ESR_mtx = 1./(I_arm_max_mtx*sqrt(2)).*(Params.dUds/100*Params.Uc_n.*NoofCells_mtx - Params.Lpcb.*Params.f_didt*1e6); % DC-link capacitor ESR vector
% Cap_C_mtx = 4.*(Params.Zeta./Cap_ESR_mtx).^2.*(Params.Lpcb + Params.Lbatt_leads + x_param(9).*NoofCells./NoofParallel_cells); % Dc-link cpacitor vector
% Cap_C_mtx = 10e-3*ones(size(I_arm_max_mtx));
% capacitor calcualtion

Z_cap_mtx = Cap_ESR_mtx + 1./(s.*Cap_C_mtx) + s*Params.Lpcb;

E_cap_sm_mtx = 0.5*Cap_C_mtx.*(U_s_sw_mtx).^2; % energy stored in the capacitor per submodule
E_cap_tot_mtx = E_cap_sm_mtx.*NoofSM_total_mtx; % total energy stored in the capacitors

% Battery and capacitor currents
Ibatt_avg_mtx = Idc_avg_t_mtx.*Z_cap_mtx./(Z_cap_mtx + Z_batt_mtx); % Maximum battery current vector
Icap_avg_mtx = Idc_avg_t_mtx.*Z_batt_mtx./(Z_cap_mtx + Z_batt_mtx); % Maximum capacitor current vector
Ibatt_avg_mtx(:,:,1) = Idc_avg_t_mtx(:,:,1); % DC current
Icap_avg_mtx(:,:,1) = 0; % DC current

Ibatt_max_mtx = Idc_max_t_mtx.*Z_cap_mtx./(Z_cap_mtx + Z_batt_mtx); % Maximum battery current vector
Icap_max_mtx = Idc_max_t_mtx.*Z_batt_mtx./(Z_cap_mtx + Z_batt_mtx); % Maximum capacitor current vector
Ibatt_max_mtx(:,:,1) = Idc_max_t_mtx(:,:,1); % DC current
Icap_max_mtx(:,:,1) = 0; % DC current

if Params.LossLim % Limit the loss calculations upto 10 kHz
    Ibatt_avg_mtx(:,:,find(F>Params.f_limit)) = 0; % equate the battery currents to zero
    Icap_avg_mtx(:,:,find(F>Params.f_limit)) = 0; % equate the capacitor currents to zero
    Ibatt_max_mtx(:,:,find(F>Params.f_limit)) = 0; % equate the battery currents to zero
    Icap_max_mtx(:,:,find(F>Params.f_limit)) = 0; % equate the capacitor currents to zero
end
            