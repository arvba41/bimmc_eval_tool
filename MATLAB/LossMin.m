function [CostVector,P_loss_total_max,Pbatt_max_tot,Pcap_max_tot,Psc_tot_max,Cap_C,NcapC,Cap_Ipk_rating_fact,Cap_Ppk_rating_fact,p_r] = LossMin(x,Params,ConsVars,EvalVars)
% Function calculates the total losses 
%
% [CostVector,P_loss_total_max,Pbatt_max_tot,Pcap_max_tot,Psc_tot_max,Cap_C,NcapC,Cap_Ipk_rating_fact,Cap_Ppk_rating_fact,p_r] = LossMin(x,Params,ConsVars,Nscells,Narms,Nsw,Delta,Nph_str)

%%%%% Uncomment the following line if you w
% load Parameters_dashboard.mat; % loading the parameters input from the user in Dashboard

% Setting-up number of phases
switch EvalVars.Nph_str
    case '3p'
        Nph = 3;
        Uph = Params.Upp/sqrt(3); % output phase voltage
        Iphavg_pk = Params.Pout/(sqrt(3)*Params.Upp*Params.cosphi); % average output current
        Iphmax_pk = Params.Pout*Params.ocf/(sqrt(3)*Params.Upp*Params.cosphi); % maximum output current
        if EvalVars.Delta 
            Uph = Params.Upp;
            Iphavg_pk = Params.Pout/(3*Params.Upp*Params.cosphi); % average output current
            Iphmax_pk = Params.Pout*Params.ocf/(3*Params.Upp*Params.cosphi); % maximum output current
        end
    case '6l'
        Nph = 6;
        Uph = Params.Upp/sqrt(3); % output phase voltage
        Iphavg_pk = Params.Pout/(6*Params.Upp/sqrt(3)*Params.cosphi); % average output current
        Iphmax_pk = Params.Pout*Params.ocf/(6*Params.Upp/sqrt(3)*Params.cosphi); % maximum output current
    case '6h'
        Nph = 6;
        Uph = Params.Upp; % output phase voltage
        Iphavg_pk = Params.Pout/(6*Params.Upp*Params.cosphi); % average output current
        Iphmax_pk = Params.Pout*Params.ocf/(6*Params.Upp*Params.cosphi); % maximum output current
    otherwise
        return;
end

% Constraint - 1
global f_didt_min Ecap_vector_sweep p_vector_sweep Enable_cons Psc_tot_avg Pbatt_avg_tot Pcap_avg_tot
f_didt_min = ConsVars.fall_didtMax_limit; % [A/s] minimum allowable didt

% Params.NPmosMin = NPmosMin; % minimum numner of parallel MOSFETs
% Params.NPmosMax = NPmosMax; % maximum number of parallel MOSFETs

% disabling Params.OptimEnable
Params.OptimEnable = 0;

% observing vector outputs
if isempty(x)
   Params.Ecap_SM_tot = Ecap_vector_sweep;
   Params.p = p_vector_sweep;
else
   Params.Ecap_SM_tot = x(1);
   Params.p = x(2);
end

% time vector
f = Params.wnom.*Params.np./120; % line frequency 
t = linspace(0,1/f,2000-1); % time instants

% vectorizing 
[~,p_mtx,t] = ndgrid(Params.Ecap_SM_tot,Params.p,t);
[Params.Ecap_SM_tot,Params.p] = ndgrid(Params.Ecap_SM_tot,Params.p,1:floor((2000)/2));

% This optimization is performed for a SSFB MMC topology with Nscells cels per
% submodule 
% Using the data from the Parameters_dashboard.mat file we get 'Params'

%%% total number of submodules

if EvalVars.Nsw == 4
    U_s = Params.Uc_min*Params.Mmax*EvalVars.Nscells; % SM DC side voltage
else
    U_s = Params.Uc_min*Params.Mmax*EvalVars.Nscells/2; % SM DC side voltage
end
[~,NoofSM_total] = DB_number_of_submodules_Calc(Uph,U_s,EvalVars.Narms,Nph);

%%% total number of parallel cells and capcity per submodule 
[BatteryCapacity_per_submodule,NoofParallel_cells] = DB_battery_capcity_No_of_parallel_cells(Params.Ebatt,Params.Uc_n,Params.DoD,EvalVars.Nscells,NoofSM_total,Params.Bcap);

%%% capacitor parameters
x_param(9)= 50e-9;
[Cap_C,Cap_ESR,Cap_Ipk_mtx,Cap_Pmax_unit,NcapC,Acap,Zeta_mmc] = DB_capacitor_calc(Params,NoofSM_total,Params.Uc_n*EvalVars.Nscells,x_param,EvalVars.Nscells,NoofParallel_cells,1,EvalVars.Nscells,Nph);

%%% Battery and capacitor currents and impedances 

% PWM signals
sawtooth_carrier = sawtooth(2*pi*f.*p_mtx.*t,0.5); % carrier wave
sineRef = Params.Mmax*cos(2*pi*f.*t); % reference wave
sineRef_inv = -Params.Mmax*cos(2*pi*f.*t); % reference wave
s = double(sineRef > sawtooth_carrier); % switching function for HB - 1
s_inv = double(sineRef_inv > sawtooth_carrier); % switching function for HB - 2

% switch current
is1_avg_t = Iphavg_pk.*s.*cos(2*pi*f.*t - acos(Params.cosphi))*sqrt(2); % Switch S1 Average currents
is3_avg_t = -Iphavg_pk.*s_inv.*cos(2*pi*f.*t - acos(Params.cosphi))*sqrt(2); % Switch S3 Average currents
is1_max_t = Iphmax_pk.*s.*cos(2*pi*f.*t - acos(Params.cosphi))*sqrt(2); % Switch S1 maximum currents
is3_max_t = -Iphmax_pk.*s_inv.*cos(2*pi*f.*t - acos(Params.cosphi))*sqrt(2); % Switch S1 maximum currents

% DC-side current 
if EvalVars.Nsw == 4
    idc_avg = (is1_avg_t + is3_avg_t)/EvalVars.Narms; % Average
    idc_max = (is1_max_t + is3_max_t)/EvalVars.Narms; % Maximum
else
    idc_avg = (is1_avg_t)/EvalVars.Narms; % Average
    idc_max = (is1_max_t)/EvalVars.Narms; % Maximum
end
                        
% calculating battery and capacitr impedances and currents 
[Z_batt,Z_cap,E_cap_tot,Ibatt_avg,Ibatt_max,Icap_avg,Icap_max] = DB_dc_side_and_battery_currents_calculation_Optimize_test(Params,squeeze(t(1,1,2:end))',idc_avg,idc_max,1,EvalVars.Nscells,3,NoofParallel_cells,Cap_ESR,Cap_C,Params.Uc_n*EvalVars.Nscells,NoofSM_total);

%%% battery and capacitor loss calculation 
[Pbatt_avg_tot,Pbatt_max,Pcap_avg_tot,Pcap_max,NcapI,Cap_Ipk_rating_fact,NcapP,Cap_Ppk_rating_fact,Pbatt_max_tot,Pcap_max_tot] = DB_battery_and_capacitor_losses_Optimize_test(Params,Ibatt_avg,Ibatt_max,Icap_avg,Icap_max,Z_batt,Z_cap,NcapC,Cap_Ipk_mtx,Cap_Pmax_unit,NoofSM_total);

%%% number of parallel mosfets
Minimum_NoofParallel_mosfets_mtx = Params.NPmosMin;
global init_npmos_opti
init_npmos_opti = 1;

global NoofParallel_actiVe_mosfets
[f_didt_calc,t_sw_max,dUds_mmc_percent,NoofParallel_mosfets,NoofParallel_actiVe_mosfets,Htfr,Rtheta_ca,Minimum_NoofParallel_mosfets_mtx] = DB_number_of_parallel_MOSFETs(Params,f,Params.p,Cap_ESR,Cap_C,Iphmax_pk/EvalVars.Narms,Iphmax_pk/EvalVars.Narms/sqrt(2),Iphmax_pk/EvalVars.Narms/pi*2*sqrt(2),Params.Rdson(EvalVars.Nscells)*1.5,Params.Uc_n*EvalVars.Nscells,EvalVars.Nsw,0,Minimum_NoofParallel_mosfets_mtx);

%%% mosfet losses calculation
[Pmos_avg,Pmos_max,Psm_avg,Psm_max,Psc_tot_avg,Psc_tot_max] = DB_MOSFET_loss_calculation(Params,Params.Uc_n*EvalVars.Nscells,Iphavg_pk/EvalVars.Narms/pi*2*sqrt(2),Iphmax_pk/EvalVars.Narms/pi*2*sqrt(2),f_didt_calc,Iphavg_pk/EvalVars.Narms/sqrt(2),Iphmax_pk/EvalVars.Narms/sqrt(2),Params.Rdson(EvalVars.Nscells),Params.Rdson(EvalVars.Nscells)*1.5,NoofParallel_actiVe_mosfets,EvalVars.Nsw,t_sw_max,f,Params.p,NoofSM_total);

%%% total losses (CostVector)
P_loss_total_max = squeeze(Psc_tot_max(:,:,1)) + Pbatt_max_tot + Pcap_max_tot;

%%% Constraints
% Considering constraints due to resonence 
L_tot_batt = Params.Lbatt_leads + x_param(9)*EvalVars.Nscells/NoofParallel_cells;
p_r = 1./(2*pi*sqrt(L_tot_batt.*Cap_C))/f; % resonence frequency pulse number

if Enable_cons
% Constraint - 1
% P_loss_total_max(Pbatt_max_tot > ConsVars.PbattMax_limit) = inf; % limiting the battery losses to 8 kW
% Psc_tot_max(Pbatt_max_tot > ConsVars.PbattMax_limit) = inf; % limiting the battery losses to 8 kW
% Pcap_max_tot(Pbatt_max_tot > ConsVars.PbattMax_limit) = inf; % limiting the battery losses to 8 kW
% Pbatt_max_tot(Pbatt_max_tot > ConsVars.PbattMax_limit) = inf; % limiting the battery losses to 8 kW

% P_loss_total_max(Cap_Ipk_rating_fact(:,:,1) > ConsVars.CapacitorCurentPeakFactor) = inf;
% Psc_tot_max(Cap_Ipk_rating_fact > ConsVars.CapacitorCurentPeakFactor) = inf;
% Pbatt_max_tot(Cap_Ipk_rating_fact(:,:,1) > ConsVars.CapacitorCurentPeakFactor) = inf;
% Pcap_max_tot(Cap_Ipk_rating_fact(:,:,1) > ConsVars.CapacitorCurentPeakFactor) = inf;

% Super constrains on capacitor current factor to be close to 1
P_loss_total_max(Cap_Ipk_rating_fact(:,:,1) > ConsVars.CapacitorCurentPeakFactor | Cap_Ipk_rating_fact(:,:,1) < Params.ccf_lowlim*ConsVars.CapacitorCurentPeakFactor) = inf;
Psc_tot_max(Cap_Ipk_rating_fact > ConsVars.CapacitorCurentPeakFactor | Cap_Ipk_rating_fact(:,:,1) < Params.ccf_lowlim*ConsVars.CapacitorCurentPeakFactor) = inf;
Pbatt_max_tot(Cap_Ipk_rating_fact(:,:,1) > ConsVars.CapacitorCurentPeakFactor | Cap_Ipk_rating_fact(:,:,1) < Params.ccf_lowlim*ConsVars.CapacitorCurentPeakFactor) = inf;
Pcap_max_tot(Cap_Ipk_rating_fact(:,:,1) > ConsVars.CapacitorCurentPeakFactor | Cap_Ipk_rating_fact(:,:,1) < Params.ccf_lowlim*ConsVars.CapacitorCurentPeakFactor) = inf;

P_loss_total_max(Params.p(:,:,1) < p_r(:,:,1)) = inf;
Psc_tot_max(Params.p(:,:,1) < p_r(:,:,1)) = inf;
Pbatt_max_tot(Params.p(:,:,1) < p_r(:,:,1)) = inf;
Pcap_max_tot(Params.p(:,:,1) < p_r(:,:,1)) = inf;
else 
    % do nothing 
end

%%% CostVector
% average losses total, Average becuase for singles values of x1 and x2, 
% we get a m x n vector with all elements equal 
CostVector = mean(P_loss_total_max,'all'); 
