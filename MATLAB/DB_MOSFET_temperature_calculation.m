function [Tc_avg_mtx,Tc_max_mtx,Tj_avg_mtx,Tj_max_mtx] = DB_MOSFET_temperature_calculation(Params,Rtheta_ca_mtx,RTheta_Jc_mtx,Psm_avg_mtx,Psm_max_mtx,Pmos_avg_mtx,Pmos_max_mtx)
% Function to calculate the case and junction temperature of the MOSFETs
%
% [Tc_avg_mtx,Tc_max_mtx,Tj_avg_mtx,Tj_max_mtx] = DB_MOSFET_temperature_calculation(Params,Rtheta_ca_mtx,RTheta_Jc_mtx,Psm_avg_mtx,Psm_max_mtx,Pmos_avg_mtx,Pmos_max_mtx)

Tc_avg_mtx = Rtheta_ca_mtx.*Psm_avg_mtx + Params.Ta; % case temperature [degC] average
Tc_max_mtx = Rtheta_ca_mtx.*Psm_max_mtx + Params.Ta; % case temperature [degC] maximum

Tj_avg_mtx = RTheta_Jc_mtx.*Pmos_avg_mtx + Tc_avg_mtx; % average junction temperautre [degC]
Tj_max_mtx = RTheta_Jc_mtx.*Pmos_max_mtx + Tc_max_mtx; % maximum junction temperautre [degC]