function [Pmos_avg_mtx,Pmos_max_mtx,Psm_avg_mtx,Psm_max_mtx,Psc_tot_avg_mtx,Psc_tot_max_mtx] = DB_MOSFET_loss_calculation(Params,U_s_sw_mtx,I_sw_av_avg_sw_mtx,I_sw_av_max_sw_mtx,f_didt_calc,I_sw_avg_sw_mtx,I_sw_max_sw_mtx,Rdson_mtx,RdsonMax_mtx,NoofParallel_actiVe_mosfets_mtx,Noofswitches_per_sm_mtx,t_sw_max_mtx,f,p_mtx,NoofSM_total_mtx)
% Function to calculate the MOSFET losses
% 
% [Pmos_avg_mtx,Pmos_max_mtx,Psm_avg_mtx,Psm_max_mtx,Psc_tot_avg_mtx,Psc_tot_max_mtx] = DB_MOSFET_loss_calculation(Params,U_s_sw_mtx,I_sw_av_avg_sw_mtx,I_sw_av_max_sw_mtx,f_didt_calc,I_sw_avg_sw_mtx,I_sw_max_sw_mtx,Rdson_mtx,RdsonMax_mtx,NoofParallel_actiVe_mosfets_mtx,Noofswitches_per_sm_mtx,t_sw_max_mtx,f,p_mtx,NoofSM_total_mtx)

% switching transients, unsing interpolation
% t_fv_max_mtx = U_s_sw_mtx./Params.f_dvdt*1e-6; % voltage fall time maximum
% t_rv_max_mtx = U_s_sw_mtx./Params.r_dvdt*1e-6; % voltage rise time maximum
% t_fi_max_mtx = I_sw_av_max_sw_mtx./Params.f_didt*1e-6; % current fall time maximum
% t_ri_max_mtx = I_sw_av_max_sw_mtx./Params.r_didt*1e-6; % current rise time maximum

t_fv_avg_mtx = U_s_sw_mtx./Params.f_dvdt; % voltage fall time average
t_rv_avg_mtx = U_s_sw_mtx./Params.r_dvdt; % voltage rise time average
t_fi_avg_mtx = I_sw_av_avg_sw_mtx./f_didt_calc; % current fall time average
t_ri_avg_mtx = I_sw_av_avg_sw_mtx./f_didt_calc; % current rise time average

t_sw_avg_mtx = t_ri_avg_mtx +t_fv_avg_mtx + t_rv_avg_mtx + t_fi_avg_mtx; % switching transient average
% t_sw_max_mtx = t_ri_max_mtx +t_fv_max_mtx + t_rv_max_mtx + t_fi_max_mtx; % switching transient maximum

Pmos_cond_avg_mtx = I_sw_avg_sw_mtx.^2.*Rdson_mtx./NoofParallel_actiVe_mosfets_mtx.^2; % Average MOSFET conduction losses
Pmos_cond_max_mtx = I_sw_max_sw_mtx.^2.*RdsonMax_mtx./NoofParallel_actiVe_mosfets_mtx.^2; % Average MOSFET conduction losses

Pmos_switching_avg_mtx = 0.5*U_s_sw_mtx.*I_sw_av_avg_sw_mtx./NoofParallel_actiVe_mosfets_mtx.*t_sw_avg_mtx.*f.*p_mtx; % Average switching losses
Pmos_switching_max_mtx = 0.5*U_s_sw_mtx.*I_sw_av_max_sw_mtx./NoofParallel_actiVe_mosfets_mtx.*t_sw_max_mtx.*f.*p_mtx; % maximum switching losses

Pmos_avg_mtx = Pmos_cond_avg_mtx + Pmos_switching_avg_mtx; % Total average MOSFET losses
Pmos_max_mtx = Pmos_cond_max_mtx + Pmos_switching_max_mtx; % Total maximum MOSFET losses

Psm_avg_mtx = Noofswitches_per_sm_mtx.*Pmos_avg_mtx.*NoofParallel_actiVe_mosfets_mtx; % Total submodule average losses
Psm_max_mtx = Noofswitches_per_sm_mtx.*Pmos_max_mtx.*NoofParallel_actiVe_mosfets_mtx; % Total submodule maximum losses

Psc_tot_avg_mtx = Psm_avg_mtx.*NoofSM_total_mtx; % Total semiconductor losses average
Psc_tot_max_mtx = Psm_max_mtx.*NoofSM_total_mtx; % Total semiconductor losses maximum
