
% Change in the peak RMS current as the numnber of cells per submodule
% increases
Ccap = [1000 330 150 100 47 33;47 47 47 47 22 22]*1e-6;
Vcap = [4 10 16 25 35 50;4 10 16 25 35 50];
ESR = [5.0 5.0 15 15 15 15;5 5 5 5 10 10]*1e-3;
Icap = [7 7 4.5 3.3 3.3 3.3;3 3 3 3 3.8 3.8];
Lcap = [7.3 7.3 7.3 7.3 7.3 7.3;5.6 5.6 5.6 5.6 5.6 5.6]*1e-3; % Capacitor unit length
Wcap = [4.3 4.3 4.3 4.3 4.3 4.3;5 5 5 5 5 5]*1e-3; % Capacitor unit width
space = 1e-3; % PCB mounting space
Acap = (Lcap+space).*(Wcap+space);
Uc_max = 4;

k=1; % Select cap type: k=1:Polymer, k=2:MLCC
Ccap_unit = interp1(Vcap(k,:),Ccap(k,:),Uc_max*[1:12],'nearest');
ESR_unit = interp1(Vcap(k,:),ESR(k,:),Uc_max*[1:12],'nearest');
Icap_unit = interp1(Vcap(k,:),Icap(k,:),Uc_max*[1:12],'nearest');
Acap_unit = interp1(Vcap(k,:),Acap(k,:),Uc_max*[1:12],'nearest');

% MOSFET 'on'-state resistance
MOSFET_Rdson = [2.5e-4 4e-4 4e-4 4e-4 4e-4 4e-4 6.8e-4 6.8e-4 6.8e-4 1.05e-3 1.05e-3 1.05e-3];
% MOSFET junction to case thermal resistance
MOSFET_Rthja = [1.4 1.2 1.2 0.61 0.61 0.61 0.5 0.5 0.5 0.48 0.48 0.48];
% MOSFET cost [€]
MOSFET_cost = [3 3 3 3 3 3 3 3 3 3 3 3];
% MOSFET via thermal resistances
Rth_pad = [3.7 10.2 10.2 4.2 4.2 4.2 4.2 4.2 4.2 1.9 1.9 1.9];

Log_rate = [1 0.9131 0.8338 0.7613 0.6951 0.6347 0.5796 0.5292 0.4832 0.4412 0.4029 0.3679];

M = [Log_rate; Ccap_unit; ESR_unit; Icap_unit; Acap_unit; MOSFET_Rdson; MOSFET_Rthja; MOSFET_cost; Rth_pad];

writematrix(M,'Vector_params.txt')

