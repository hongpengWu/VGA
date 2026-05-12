module vga_red(
    iclk_50,
    irst,
    key_up,
    key_down,
    key_left,
    key_right,
    ovga_clock,
    ovga_hs,
    ovga_vs,
    ovga_blank,
    ovga_sync,
    ovga_r,
    ovga_g,
    ovga_b,
    ovga_r0,
    ovga_g0,
    ovga_b0
);

// ==================== 按 DE2 板引脚分配 ====================
// 时钟与复位
(* chip_pin = "N2"  *) input  iclk_50;   // CLOCK_50
(* chip_pin = "N25" *) input  irst;      // SW[0]，高电平复位

// 方向按键，低电平有效
(* chip_pin = "W26" *) input key_up;     // KEY[3]
(* chip_pin = "P23" *) input key_down;   // KEY[2]
(* chip_pin = "N23" *) input key_left;   // KEY[1]
(* chip_pin = "G26" *) input key_right;  // KEY[0]

// VGA 控制信号
(* chip_pin = "B8" *) output ovga_clock; // VGA_CLK
(* chip_pin = "D6" *) output ovga_blank; // VGA_BLANK
(* chip_pin = "B7" *) output ovga_sync;  // VGA_SYNC
(* chip_pin = "A7" *) output reg ovga_hs;// VGA_HS
(* chip_pin = "D8" *) output reg ovga_vs;// VGA_VS

// RGB：8bit 主数据 + 2bit 低位补0
(* chip_pin = "E10,F11,H12,H11,A8,C9,D9,G10" *) output reg [7:0] ovga_r;
(* chip_pin = "D12,E12,D11,G11,A10,B10,D10,C10" *) output reg [7:0] ovga_g;
(* chip_pin = "B12,C12,B11,C11,J11,J10,G12,F12" *) output reg [7:0] ovga_b;

(* chip_pin = "F10,C8" *) output [1:0] ovga_r0;
(* chip_pin = "A9,B9"  *) output [1:0] ovga_g0;
(* chip_pin = "J14,J13" *) output [1:0] ovga_b0;
// ============================================================

parameter H_TA    = 96;
parameter H_TB    = 40;
parameter H_TC    = 8;
parameter H_TD    = 640;
parameter H_TE    = 8;
parameter H_TF    = 8;
parameter H_BLANK = H_TA + H_TB + H_TC;
parameter H_DATA  = H_BLANK + H_TD;
parameter H_TOTAL = H_TA + H_TB + H_TC + H_TD + H_TE + H_TF;

parameter V_TA    = 2;
parameter V_TB    = 25;
parameter V_TC    = 8;
parameter V_TD    = 480;
parameter V_TE    = 8;
parameter V_TF    = 2;
parameter V_BLANK = V_TA + V_TB + V_TC;
parameter V_DATA  = V_BLANK + V_TD;
parameter V_TOTAL = V_TA + V_TB + V_TC + V_TD + V_TE + V_TF;

reg        iclk;
reg [10:0] h_cont, v_cont;

// 上电后先保持一小段时间复位，避免配置完成后内部状态未初始化就开始跑游戏逻辑
reg [20:0] startup_cnt = 21'd0;
reg        startup_reset = 1'b1;
wire       reset = irst | startup_reset;

// 上电释放后的内部复位
always @(posedge iclk_50 or posedge irst) begin
    if (irst) begin
        startup_cnt   <= 21'd0;
        startup_reset <= 1'b1;
    end else if (startup_reset) begin
        if (startup_cnt == 21'd1_999_999)
            startup_reset <= 1'b0;
        else
            startup_cnt <= startup_cnt + 21'd1;
    end
end

// 50MHz 分频成 25MHz 像素时钟
always @(posedge iclk_50) begin
    if (reset)
        iclk <= 1'b0;
    else
        iclk <= ~iclk;
end

assign ovga_sync  = 1'b1;
assign ovga_blank = ~((h_cont < H_BLANK) || (h_cont >= H_DATA) ||
                      (v_cont < V_BLANK) || (v_cont >= V_DATA));
assign ovga_clock = ~iclk;

assign ovga_r0 = 2'b00;
assign ovga_g0 = 2'b00;
assign ovga_b0 = 2'b00;

// ==================== VGA 时序产生 ====================
// 行扫描
always @(posedge iclk) begin
    if (reset)
        h_cont <= 11'd0;
    else if (h_cont == H_TOTAL - 1)
        h_cont <= 11'd0;
    else
        h_cont <= h_cont + 11'd1;
end

// 场扫描
always @(posedge iclk) begin
    if (reset)
        v_cont <= 11'd0;
    else if (h_cont == H_TOTAL - 1) begin
        if (v_cont == V_TOTAL - 1)
            v_cont <= 11'd0;
        else
            v_cont <= v_cont + 11'd1;
    end
end

// hsync
always @(posedge iclk) begin
    if (reset)
        ovga_hs <= 1'b1;
    else if (h_cont <= H_TA - 1)
        ovga_hs <= 1'b0;
    else
        ovga_hs <= 1'b1;
end

// vsync
always @(posedge iclk) begin
    if (reset)
        ovga_vs <= 1'b1;
    else if (v_cont <= V_TA - 1)
        ovga_vs <= 1'b0;
    else
        ovga_vs <= 1'b1;
end

// ==================== 贪吃蛇游戏逻辑 ====================

// 网格坐标，将640x480的屏幕划分为 40x30 的网格，每格 16x16
wire [5:0] block_x = (h_cont >= H_BLANK) ? ((h_cont - H_BLANK) >> 4) : 6'd0;
wire [4:0] block_y = (v_cont >= V_BLANK) ? ((v_cont - V_BLANK) >> 4) : 5'd0;

// 游戏主时钟，产生移动节拍
// 50MHz 时钟，除以 25_000_000 = 2Hz，避免显示器刚同步完成时蛇已经撞墙
reg [24:0] game_clk_cnt;
reg game_tick;
always @(posedge iclk_50) begin
    if (reset) begin
        game_clk_cnt <= 0;
        game_tick <= 0;
    end else begin
        if (game_clk_cnt >= 25'd24999999) begin
            game_clk_cnt <= 0;
            game_tick <= 1;
        end else begin
            game_clk_cnt <= game_clk_cnt + 1;
            game_tick <= 0;
        end
    end
end

// 生成 100Hz 时钟供消抖模块使用
// 50MHz / 500,000 = 100Hz -> 翻转阈值 250,000 (0 到 249,999)
reg [17:0] clk_100Hz_cnt;
reg clk_100Hz;
always @(posedge iclk_50) begin
    if (reset) begin
        clk_100Hz_cnt <= 0;
        clk_100Hz <= 0;
    end else begin
        if (clk_100Hz_cnt >= 18'd249_999) begin
            clk_100Hz_cnt <= 0;
            clk_100Hz <= ~clk_100Hz;
        end else begin
            clk_100Hz_cnt <= clk_100Hz_cnt + 1;
        end
    end
end

// 实例化消抖模块
wire key_up_db, key_down_db, key_left_db, key_right_db;

// 修改了 debounce 初始值为 1'b1，以防止上电瞬间误判为按键按下
debounce db_up   (.pb(key_up),    .clock_100Hz(clk_100Hz), .pb_debounced(key_up_db));
debounce db_down (.pb(key_down),  .clock_100Hz(clk_100Hz), .pb_debounced(key_down_db));
debounce db_left (.pb(key_left),  .clock_100Hz(clk_100Hz), .pb_debounced(key_left_db));
debounce db_right(.pb(key_right), .clock_100Hz(clk_100Hz), .pb_debounced(key_right_db));

// 方向控制：0=上, 1=下, 2=左, 3=右
reg [1:0] dir;
reg       game_started;

always @(posedge iclk_50) begin
    if (reset) begin
        dir <= 2'd3; // 默认向右
        game_started <= 1'b0;
    end else begin
        if (!game_started) begin
            // 游戏尚未开始时，允许任意方向作为首次方向
            if (!key_up_db) begin
                dir <= 2'd0;
                game_started <= 1'b1;
            end else if (!key_down_db) begin
                dir <= 2'd1;
                game_started <= 1'b1;
            end else if (!key_left_db) begin
                dir <= 2'd2;
                game_started <= 1'b1;
            end else if (!key_right_db) begin
                dir <= 2'd3;
                game_started <= 1'b1;
            end
        end else begin
            // 游戏开始后，禁止直接反向
            if (!key_up_db && dir != 2'd1)
                dir <= 2'd0;
            else if (!key_down_db && dir != 2'd0)
                dir <= 2'd1;
            else if (!key_left_db && dir != 2'd3)
                dir <= 2'd2;
            else if (!key_right_db && dir != 2'd2)
                dir <= 2'd3;
        end
    end
end

// 蛇身数组和长度
parameter MAX_LENGTH = 64;
reg [5:0] snake_x [0:MAX_LENGTH-1];
reg [4:0] snake_y [0:MAX_LENGTH-1];
reg [6:0] snake_len;

// 苹果坐标与伪随机数生成器(LFSR)
reg [5:0] apple_x;
reg [4:0] apple_y;
reg [10:0] lfsr;

always @(posedge iclk_50 or posedge irst) begin
    if (irst) begin
        lfsr <= 11'h7FF;
    end else begin
        // 11位 LFSR 简单多项式
        lfsr <= {lfsr[9:0], lfsr[10] ^ lfsr[8]};
    end
end

// 游戏主逻辑
reg game_over;
integer k;
reg hit_body;
reg [5:0] next_x;
reg [4:0] next_y;

always @(posedge iclk_50) begin
    if (reset) begin
        // 初始化蛇：位于屏幕中央，长度为3
        snake_x[0] <= 6'd20; snake_y[0] <= 5'd15;
        snake_x[1] <= 6'd19; snake_y[1] <= 5'd15;
        snake_x[2] <= 6'd18; snake_y[2] <= 5'd15;
        for (k = 3; k < MAX_LENGTH; k = k + 1) begin
            snake_x[k] <= 6'd0;
            snake_y[k] <= 5'd0;
        end
        snake_len <= 7'd3;
        
        // 初始苹果位置
        apple_x <= 6'd30;
        apple_y <= 5'd15;
        game_over <= 0;
    end else if (game_tick && game_started && !game_over) begin
        // 计算下一个头的位置
        next_x = snake_x[0];
        next_y = snake_y[0];
        hit_body = 1'b0;
        case (dir)
            2'd0: next_y = snake_y[0] - 1; // 上
            2'd1: next_y = snake_y[0] + 1; // 下
            2'd2: next_x = snake_x[0] - 1; // 左
            2'd3: next_x = snake_x[0] + 1; // 右
        endcase

        // 碰撞检测 - 撞墙
        // 因为 next_x/y 是无符号数，减1下溢出变成全1(大于39或29)
        if (next_x >= 40 || next_y >= 30) begin
            game_over <= 1;
        end else begin
            // 碰撞检测 - 撞自己
            for (k = 1; k < MAX_LENGTH; k = k + 1) begin
                if (k < snake_len && next_x == snake_x[k] && next_y == snake_y[k])
                    hit_body = 1'b1;
            end

            if (hit_body) begin
                game_over <= 1;
            end else begin
                // 身体移动
                for (k = MAX_LENGTH - 1; k > 0; k = k - 1) begin
                    if (k < snake_len) begin
                        snake_x[k] <= snake_x[k-1];
                        snake_y[k] <= snake_y[k-1];
                    end
                end
                // 头部移动
                snake_x[0] <= next_x;
                snake_y[0] <= next_y;
                
                // 吃苹果
                if (next_x == apple_x && next_y == apple_y) begin
                    if (snake_len < MAX_LENGTH) begin
                        snake_len <= snake_len + 1;
                    end
                    // 更新苹果位置，保证在40x30范围内
                    apple_x <= (lfsr[5:0] >= 40) ? lfsr[5:0] - 24 : lfsr[5:0];
                    apple_y <= (lfsr[10:6] >= 30) ? lfsr[10:6] - 2 : lfsr[10:6];
                end
            end
        end
    end
end

// 渲染图像生成
integer j;
reg is_snake;
reg is_apple;

always @(*) begin
    is_snake = 0;
    for (j = 0; j < MAX_LENGTH; j = j + 1) begin
        if (j < snake_len && block_x == snake_x[j] && block_y == snake_y[j]) begin
            is_snake = 1;
        end
    end
    is_apple = (block_x == apple_x && block_y == apple_y);
end

wire display_area = (h_cont >= H_BLANK) && (h_cont < H_DATA) && 
                    (v_cont >= V_BLANK) && (v_cont < V_DATA);

// 为了避免画面闪烁，我们将渲染寄存一拍或者直接在像素时钟下输出
always @(posedge iclk) begin
    if (reset) begin
        ovga_r <= 8'h00;
        ovga_g <= 8'h00;
        ovga_b <= 8'h00;
    end else if (display_area) begin
        if (game_over) begin
            // 游戏结束：显示偏红色背景
            ovga_r <= 8'h88;
            ovga_g <= 8'h00;
            ovga_b <= 8'h00;
        end else if (is_snake) begin
            // 蛇身：绿色
            ovga_r <= 8'h00;
            ovga_g <= 8'hFF;
            ovga_b <= 8'h00;
        end else if (is_apple) begin
            // 苹果：红色
            ovga_r <= 8'hFF;
            ovga_g <= 8'h00;
            ovga_b <= 8'h00;
        end else begin
            // 背景：黑色，可加入边界判断画边框
            if (block_x == 0 || block_x == 39 || block_y == 0 || block_y == 29) begin
                // 边框蓝色
                ovga_r <= 8'h00;
                ovga_g <= 8'h00;
                ovga_b <= 8'hFF;
            end else begin
                ovga_r <= 8'h00;
                ovga_g <= 8'h00;
                ovga_b <= 8'h00;
            end
        end
    end else begin
        // 屏幕消隐区
        ovga_r <= 8'h00;
        ovga_g <= 8'h00;
        ovga_b <= 8'h00;
    end
end

endmodule
//消抖
module debounce (
    input  wire pb,
    input  wire clock_100Hz,
    output reg  pb_debounced = 1'b1  // 修改初始值为 1，避免上电/复位后输出低电平引发误触发
);

    reg [3:0] shift_pb = 4'b1111; // 初始化移位寄存器为全1

    always @(posedge clock_100Hz) begin
        shift_pb <= {shift_pb[2:0], pb};
        if (shift_pb == 4'b1111) begin
            pb_debounced <= 1'b1;
        end else if (shift_pb == 4'b0000) begin
            pb_debounced <= 1'b0;
        end
    end

endmodule
