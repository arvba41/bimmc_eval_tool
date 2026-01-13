%% Function to calculate determine the DC charging capailities of DSFB topology
clear all
clc
%% Definitions
Uph = 440/sqrt(3); % AC phase voltage 
Nscells = 5; % Number of cascaded cells per SM
Usm = 3.7; % submodule RMS AC voltage 
Narms = 2; % number of arms per phase
Nph = 3 ; % total number of phases
Nsw = 2; % number of switches per SM (2 for FB and 1 for HB)

Ebatt = 1e6; % energy of the batery pack
DoD = 0.6; % depth of discharge 
Bcap = 24; % battery capcity per cell

Udc_chrg = 800; % DC charging voltage
Pdc_chrg = 1e6; % DC charging power

Uc_n = 3.7; % nominal cell voltage
Uc_min = 3.45; % minimum cell voltage
Uc_max = 4.2; % maximum cell voltage

Rth_pad = 4.2; % thermal resistance of the contact MOSFET pad 

Params.NPmosMax = 20; % maximum number of parallel MOSFETs
Params.Tc = 80; % Maximum case temperature 
Params.Ta = 40; % Maximum ambient temperature
RdsonMax = 4e-4*1.5; % Maximum on-state resistance of MOSFETs
Npmos_min = 2; % minimum number of parallel MOSFETs
Params.Amos = 0.0004; % MOSFET Area

Params.AlelionEnable = 1; % Using Alelion cell battery EIS
Params.DC_imp_freq = 1; % DC impedance frequency

C_cap = 0.0052; % DC-link cpacitor capacitance 
ESR_cap = 4.3161e-04; % DC-link cpacitor ESR
Params.Lpcb = 2e-9; % pcb stray inductance
f_sw = 2*5e3; % switchinig frequency [Hz]
Params.Lbatt_leads = 2e-7; % battery leads inductace [H]
%% Basic calculations
%%% Number of Submodules
[~,NoofSM_total] = DB_number_of_submodules_Calc(Uph,Uc_min*Nscells*0.85,Narms,Nph); % Matlab function to calculate the number of submodules

%%% number of parallel cells

[BatteryCapacity_per_submodule,NoofParallel_cells] = DB_battery_capcity_No_of_parallel_cells(Ebatt,Uc_n,DoD,Nscells,NoofSM_total,Bcap);

%%% DC link voltages for charging
U_dc_nom = NoofSM_total./Nph.*Nscells*Uc_n % nominal DC voltage
U_dc_min = NoofSM_total./Nph.*Nscells*Uc_min % Minimum DC voltage
U_dc_max = NoofSM_total./Nph.*Nscells*Uc_max % Maximum DC voltage

% Iarm_chrg = Pdc_chrg/Udc_chrg/Nph % DC arm charging current
Iarm_chrg_max = Pdc_chrg/Udc_chrg/Nph % DC arm charging current

%% Discrete Mode
% discrete modules are considers the submodules as discrete battery modules
% that can be either inserted when the SM DC voltage is lower than the
% average and bypassed when the SM DC voltage is higher than the cell
% voltage limits. 

% number of parallel MOSFETs
% [NoofParallel_mosfets,NoofParallel_actiVe_mosfets,Rtheta_ca,Npmos_min] = DB_number_of_parallel_MOSFETs_discrete_DC_charging(Params,Iarm_chrg,RdsonMax,Nsw,Npmos_min,Rth_pad);
NoofParallel_mosfets = Iarm_chrg_max*sqrt(RdsonMax*Rth_pad/(Params.Tc-Params.Ta));
NoofParallel_actiVe_mosfets = max(Npmos_min,min(NoofParallel_mosfets,Params.NPmosMax));
% Battery losses

[Z_batt_mtx] = DB_dc_side_and_battery_currents_DC_charging_discrete(Params,Nscells,NoofParallel_cells); % battery impedance
Pbatt_sm = Iarm_chrg_max.^2.*Z_batt_mtx; % battery losses per submodule
Pbatt_tot = NoofSM_total.*Pbatt_sm; % battery losses total

% semiconductor losses

Imos = Iarm_chrg_max/NoofParallel_actiVe_mosfets; % MOSFET current 
Pcmos = Iarm_chrg_max.^2./NoofParallel_actiVe_mosfets.^2.*RdsonMax; % conduction losses per MOSFET
Pcsw = Pcmos.*NoofParallel_actiVe_mosfets; % conduction losses per switch
Psm = Pcsw*Nsw; % conduction losses per submodule
Psctot = Psm*NoofSM_total; % total conduction losses

% verificaltion of temperature rise
dTca_calc = Pcsw*Rth_pad/NoofParallel_actiVe_mosfets;

Ptot = Psctot; % total SC losses at 1MW

%% Analog Mode
% Every submodule is considered as a DC-DC converter.

NoofSM_perPh = NoofSM_total./Nph; % number of submodules per phase
Usm_req = Udc_chrg./NoofSM_perPh; % required SM output voltage 

D_sm_nom = Usm_req/Nscells/Uc_n; % Duty cycle per submodule nominal
D_sm_min = Usm_req/Nscells/Uc_max; % Duty cycle per submodule minimum
D_sm_max = Usm_req/Nscells/Uc_min; % Duty cycle per submodule maximum

% calculating the DC side currents of the submodule
fs = 1e6; % sample frequency
t = 0:1/fs:1/333.333; % time interval
carr = sawtooth(2*pi*f_sw*t,0.5); % carrier waveform
s_sm_up = double(D_sm_min > carr); % switchinjg function upper MOSFET
s_sm_down = double(D_sm_min <= carr); % switching function lower MOSFET

i_dc_chrg = s_sm_up.*Iarm_chrg_max; % DC-side SM currents
% battery and capacitor currents
[Z_batt_mtx,Z_cap_mtx,E_cap_tot_mtx,Ibatt_max_chrg,Icap_max_chrg,F] = DB_dc_side_and_battery_currents_dcdc_chrg_calculation(Params,t,i_dc_chrg,Nscells,NoofParallel_cells,ESR_cap,C_cap,Usm_req,NoofSM_total);

% battery and capacitor losses
Pbatt_loss_dc_chrg = Ibatt_max_chrg.*conj(Ibatt_max_chrg).*real(Z_batt_mtx); % battery losses
Pcap_loss_dc_chrg = Icap_max_chrg.*conj(Icap_max_chrg).*real(Z_cap_mtx); % capacitor losses

% MOSFET losses and number of parallel MOSFETs 
% P ; % total losses per MOSFET

%% Battery Capacity and number of parallel cells per submodule
% [BatteryCapacity_per_submodule,NoofParallel_cells] = DB_battery_capcity_No_of_parallel_cells(Params.Ebatt,Params.Uc_n,Params.DoD,NoofCells_mtx,NoofSM_total_mtx,Params.Bcap);